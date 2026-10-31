"""Bounded original-art parity and the public graphics compiler contract."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "game-art"


def compiler():
    path = ROOT / "scripts" / "compile_graphics.py"
    assert path.is_file(), "the standalone graphics compiler is not implemented"
    spec = importlib.util.spec_from_file_location("compile_graphics", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def test_original_entry_planes_match_cp64_reference(tmp_path):
    paths, metadata = compiler().compile_assets(tmp_path)
    reference = json.loads((ASSETS / "cp64-manifest.json").read_text())["generated_bins"]
    expected = {
        "charset": "charset.bin",
        "title_screen": "title/one/screen.bin",
        "title_color": "title/one/color.bin",
        "info_screen": "info/screen.bin",
        "info_color": "info/color.bin",
        "board_bitmap": "game/blank/bitmap.bin",
        "board_screen": "game/blank/screen.bin",
        "board_color": "game/blank/color.bin",
    }
    for name, original in expected.items():
        payload = paths[name].read_bytes()
        assert len(payload) == reference[original]["bytes"]
        assert digest(payload) == reference[original]["sha256"]
    assert metadata["format"] == "falken9-graphics-v1"


def region_bytes(paths, metadata, name):
    record = metadata["regions"][name]
    return paths["packed"].read_bytes()[record["offset"]:record["offset"] + record["length"]]


def apply_cell(paths, metadata, planes, cell, mark):
    for plane_name, descriptor in metadata["cells"][cell]["planes"].items():
        values = region_bytes(paths, metadata, descriptor["values"][mark])
        offsets = descriptor["destination_offsets"]
        assert len(values) == len(offsets)
        for offset, value in zip(offsets, values):
            planes[plane_name][offset] = value


def test_packed_regions_restore_exact_reference_marks_without_neighbor_writes(tmp_path):
    paths, metadata = compiler().compile_assets(tmp_path)
    assert "packed" in paths, "contiguous graphics transport is missing"
    packed = paths["packed"].read_bytes()
    regions = metadata["regions"]
    cursor = 0
    for name, record in regions.items():
        assert record["offset"] == cursor, name
        payload = region_bytes(paths, metadata, name)
        assert digest(payload) == record["sha256"]
        cursor += record["length"]
    assert len(packed) == cursor == metadata["packed"]["length"]
    assert digest(packed) == metadata["packed"]["sha256"]
    for name in ("charset", "title_screen", "title_color", "info_screen", "info_color",
                 "board_bitmap", "board_screen", "board_color"):
        assert region_bytes(paths, metadata, name) == paths[name].read_bytes()
    base = {p: bytearray(paths[f"board_{p}"].read_bytes()) for p in ("bitmap", "screen", "color")}
    assert list(metadata["cells"]) == list("abcdefghi")
    reference = json.loads((ASSETS / "cp64-manifest.json").read_text())["generated_bins"]
    for mark in "xo":
        planes = {p: bytearray(data) for p, data in base.items()}
        written = {p: set() for p in base}
        for cell in "abcdefghi":
            descriptor = metadata["cells"][cell]
            assert descriptor["square"] == "abcdefghi".index(cell) + 1
            for plane_name, plane in descriptor["planes"].items():
                offsets = plane["destination_offsets"]
                assert offsets == sorted(set(offsets))
                assert not (set(offsets) & written[plane_name]), (cell, plane_name)
                written[plane_name].update(offsets)
                raw = region_bytes(paths, metadata, plane["offsets_region"])
                assert list(int.from_bytes(raw[i:i+2], "little") for i in range(0, len(raw), 2)) == offsets
                assert plane["destination_base"] == {"bitmap": 0x2000, "screen": 0x0400, "color": 0xd800}[plane_name]
                assert all(0 <= n < len(base[plane_name]) for n in offsets)
            apply_cell(paths, metadata, planes, cell, mark)
        for name, data in planes.items():
            assert digest(data) == reference[f"game/all-{mark}/{name}.bin"]["sha256"]
    assert json.loads(paths["metadata"].read_text()) == metadata


@pytest.mark.parametrize("relative", json.loads((ASSETS / "provenance.json").read_text())["sources"])
def test_changed_original_source_is_rejected_before_output(tmp_path, relative):
    source = tmp_path / "source"
    shutil.copytree(ASSETS, source)
    target = source / relative
    target.write_bytes(target.read_bytes() + b"changed")
    module = compiler()
    module.ASSETS = source
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="source integrity"):
        module.compile_assets(output)
    assert not output.exists()


def test_compiler_checks_reference_plane_digests_not_just_png_integrity(tmp_path):
    source = tmp_path / "source"
    shutil.copytree(ASSETS, source)
    manifest_path = source / "cp64-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["generated_bins"]["charset.bin"]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest))
    provenance_path = source / "provenance.json"
    provenance = json.loads(provenance_path.read_text())
    provenance["sources"]["cp64-manifest.json"].update(
        bytes=manifest_path.stat().st_size, sha256=digest(manifest_path.read_bytes()))
    provenance_path.write_text(json.dumps(provenance))
    module = compiler()
    module.ASSETS = source
    with pytest.raises(ValueError, match="reference plane.*charset.bin"):
        module.compile_assets(tmp_path / "out")


def test_isolated_stdlib_build_has_only_requested_planes_and_is_deterministic(tmp_path):
    """No installed packages, git metadata, network, or neighboring CP64 checkout."""
    isolated = tmp_path / "standalone"
    script = isolated / "scripts" / "compile_graphics.py"
    script.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "scripts" / "compile_graphics.py", script)
    shutil.copytree(ASSETS, isolated / "assets" / "game-art")
    outputs = []
    for name in ("first", "second"):
        output = isolated / name
        result = subprocess.run([sys.executable, "-I", "-S", str(script), "--output", str(output)],
                                cwd=tmp_path, text=True, capture_output=True, check=True)
        assert not result.stderr
        parsed = json.loads(result.stdout)
        paths = parsed["paths"]
        files = {str(p.relative_to(output)): p.read_bytes() for p in output.rglob("*") if p.is_file()}
        assert set(files) == {str(Path(path).relative_to(output)) for path in paths.values()}, "unexpected generated planes"
        outputs.append(files)
    assert outputs[0] == outputs[1]
    metadata = json.loads(outputs[0]["graphics.json"])
    assert metadata["source_provenance"]["sha256"] == digest((ASSETS / "provenance.json").read_bytes())


def decode_bitmap(planes, background=0):
    pixels = bytearray(160 * 200)
    for y in range(200):
        for x in range(160):
            cell = (y // 8) * 40 + x // 4
            pair = (planes["bitmap"][cell * 8 + y % 8] >> (6 - 2 * (x % 4))) & 3
            choices = (background, planes["screen"][cell] >> 4,
                       planes["screen"][cell] & 15, planes["color"][cell] & 15)
            pixels[y * 160 + x] = choices[pair]
    return pixels


def test_vic_contract_decodes_original_views_and_mixed_mark_sequences(tmp_path):
    module = compiler()
    paths, metadata = module.compile_assets(tmp_path)
    assert "vic" in metadata, "VIC bank/mode/copy contract is missing"
    vic = metadata["vic"]
    assert vic["bank_base"] == (3 - vic["dd00_low_bits"]) * 0x4000 == 0
    for view in ("title", "info", "game"):
        config = vic[view]
        assert (config["d018"] >> 4) * 1024 == 0x0400
        if view == "game":
            assert (config["d018"] & 8) * 1024 == 0x2000
            assert config["d011"] & 0x20 and config["d016"] & 0x10
            assert config["copies"] == {"board_bitmap": 0x2000, "board_screen": 0x0400, "board_color": 0xd800}
        else:
            assert (config["d018"] & 14) * 1024 == 0x3000
            assert not (config["d011"] & 0x20 or config["d016"] & 0x10)
            assert config["copies"] == {"charset": 0x3000, f"{view}_screen": 0x0400, f"{view}_color": 0xd800}
            screen, color, charset = (paths[f"{view}_screen"].read_bytes(),
                                      paths[f"{view}_color"].read_bytes(), paths["charset"].read_bytes())
            decoded = bytearray(320 * 200)
            for cell in range(1000):
                row, column = divmod(cell, 40)
                for y in range(8):
                    mask = charset[screen[cell] * 8 + y]
                    for x in range(8):
                        decoded[(row * 8 + y) * 320 + column * 8 + x] = color[cell] if mask & (128 >> x) else vic["background"]
            expected_image = bytearray(module.read_indexed_png(ASSETS / view / "image.png").pixels)
            if view == "title":
                # CP64's entry compiler normalizes hotkey/selection colors;
                # these reviewed JSON deltas are not edits to the source PNG.
                selection = json.loads((ASSETS / "title/selection.json").read_text())
                active = selection["highlight"]["active_color"]
                inactive = selection["highlight"]["inactive_color"]
                for state, geometry in selection["states"].items():
                    columns = {geometry["hotkey_column"]: active}
                    columns.update({c: active if state == "one" else inactive
                                    for c in range(geometry["text_start_column"],
                                                   geometry["text_start_column"] + geometry["text_width"])})
                    for column, ink in columns.items():
                        for y in range(8):
                            for x in range(8):
                                offset = (geometry["row"] * 8 + y) * 320 + column * 8 + x
                                if expected_image[offset]:
                                    expected_image[offset] = ink
            assert decoded == expected_image
    base = {p: bytearray(paths[f"board_{p}"].read_bytes()) for p in ("bitmap", "screen", "color")}
    blank_pixels = decode_bitmap(base)
    marks = {mark: module.read_indexed_png(ASSETS / f"game/marks/{mark}.png").pixels for mark in "xo"}
    layout = json.loads((ASSETS / "game/board/layout.json").read_text())["cell_rectangles"]
    patterns = [mark * 9 for mark in "xo"] + ["xoxoxoxox", "oxoxoxoxo"]
    patterns += ["." * i + mark + "." * (8 - i) for i in range(9) for mark in "xo"]
    for pattern in patterns:
        planes = {p: bytearray(data) for p, data in base.items()}
        expected = bytearray(blank_pixels)
        for i in reversed(range(9)):
            mark = pattern[i]
            if mark == ".":
                continue
            cell = "abcdefghi"[i]
            apply_cell(paths, metadata, planes, cell, mark)
            left, top, width, height = layout[cell]["logical_xywh"]
            for y in range(height):
                for x in range(width):
                    pixel = marks[mark][y * width + x]
                    if pixel:
                        expected[(top + y) * 160 + left + x] = pixel
            # The original CP64 compiler shares one Color RAM accent per
            # destination 4x8 cell. Its unaligned O crops map these original
            # secondary-color pixels between 13/14; preserve that byte-exact
            # behavior rather than silently repainting the imported art.
            original_o_accents = {
                "a": [(5, 4, 13), (4, 5, 13), (4, 6, 13), (5, 6, 13), (4, 8, 13)],
                "b": [(5, 4, 13), (6, 4, 13), (4, 5, 13), (4, 6, 13),
                      (5, 6, 13), (6, 6, 13), (4, 8, 13)],
                "d": [(3, 7, 14), (3, 8, 14)], "e": [(3, 7, 14), (3, 8, 14)],
                "g": [(3, 7, 14), (3, 8, 14)], "h": [(3, 7, 14), (3, 8, 14)],
            }
            if mark == "o":
                for x, y, ink in original_o_accents.get(cell, []):
                    expected[(top + y) * 160 + left + x] = ink
            assert decode_bitmap(planes) == expected, (pattern, cell)
