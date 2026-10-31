#!/usr/bin/env python3
"""Compile original CP64 indexed art using only the Python standard library.

Adapted from CP64 scripts/compile_c64_assets.py (Apache-2.0).
Original identity and modification boundary: assets/game-art/provenance.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "game-art"
OUTPUT = ROOT / "build" / "graphics"

# C64 Pepto palette; every source PNG is indexed directly by VIC-II color ID.
C64_PALETTE = (
    (0x00, 0x00, 0x00), (0xFF, 0xFF, 0xFF), (0x68, 0x37, 0x2B), (0x70, 0xA4, 0xB2),
    (0x6F, 0x3D, 0x86), (0x58, 0x8D, 0x43), (0x35, 0x28, 0x79), (0xB8, 0xC7, 0x6F),
    (0x6F, 0x4F, 0x25), (0x43, 0x39, 0x00), (0x9A, 0x67, 0x59), (0x44, 0x44, 0x44),
    (0x6C, 0x6C, 0x6C), (0x9A, 0xD2, 0x84), (0x6C, 0x5E, 0xB5), (0x95, 0x95, 0x95),
)
TITLE_STATES = ("auto", "one", "two")
SOURCE_PNGS = (
    "title/image.png", "info/image.png",
    "game/board/bitmap-selectors.png", "game/board/screen-hi.png", "game/board/screen-lo.png", "game/board/color-lo.png",
    "game/marks/x.png", "game/marks/o.png",
)


class IndexedPNG:
    def __init__(self, width: int, height: int, palette: tuple[tuple[int, int, int], ...], pixels: bytes):
        self.width, self.height, self.palette, self.pixels = width, height, palette, pixels


def paeth(a: int, b: int, c: int) -> int:
    estimate = a + b - c
    da, db, dc = abs(estimate - a), abs(estimate - b), abs(estimate - c)
    return a if da <= db and da <= dc else b if db <= dc else c


def read_indexed_png(path: Path) -> IndexedPNG:
    payload = path.read_bytes()
    if payload[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path}: not a PNG")
    width = height = bit_depth = color_type = interlace = None
    palette = None
    compressed = bytearray()
    cursor = 8
    while cursor < len(payload):
        length = struct.unpack(">I", payload[cursor:cursor + 4])[0]
        kind = payload[cursor + 4:cursor + 8]
        chunk = payload[cursor + 8:cursor + 8 + length]
        cursor += length + 12
        if kind == b"IHDR":
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunk)
            if compression or filtering:
                raise ValueError(f"{path}: unsupported PNG compression/filter method")
        elif kind == b"PLTE":
            if len(chunk) != 48:
                raise ValueError(f"{path}: palette must have exactly 16 C64 entries")
            palette = tuple((chunk[index], chunk[index + 1], chunk[index + 2]) for index in range(0, 48, 3))
        elif kind == b"IDAT":
            compressed.extend(chunk)
        elif kind == b"IEND":
            break
    if None in (width, height) or bit_depth != 8 or color_type != 3 or interlace != 0 or palette is None:
        raise ValueError(f"{path}: expected a non-interlaced 8-bit indexed PNG")
    if palette != C64_PALETTE:
        raise ValueError(f"{path}: palette must be the project C64 palette")
    raw = zlib.decompress(compressed)
    if len(raw) != (width + 1) * height:
        raise ValueError(f"{path}: unexpected decompressed size")
    decoded = bytearray(width * height)
    previous = bytearray(width)
    cursor = 0
    for y in range(height):
        filter_kind = raw[cursor]; cursor += 1
        encoded = raw[cursor:cursor + width]; cursor += width
        row = bytearray(width)
        for x, value in enumerate(encoded):
            left, above, upper_left = (row[x - 1] if x else 0), previous[x], (previous[x - 1] if x else 0)
            if filter_kind == 0: row[x] = value
            elif filter_kind == 1: row[x] = (value + left) & 0xff
            elif filter_kind == 2: row[x] = (value + above) & 0xff
            elif filter_kind == 3: row[x] = (value + ((left + above) // 2)) & 0xff
            elif filter_kind == 4: row[x] = (value + paeth(left, above, upper_left)) & 0xff
            else: raise ValueError(f"{path}: unsupported PNG row filter {filter_kind}")
        decoded[y * width:(y + 1) * width] = row
        previous = row
    return IndexedPNG(width, height, palette, bytes(decoded))


def require_pixels(source: Path, relative: str, width: int, height: int) -> bytes:
    image = read_indexed_png(source / relative)
    if (image.width, image.height) != (width, height):
        raise ValueError(f"{relative}: expected {width}×{height}, got {image.width}×{image.height}")
    return image.pixels


def write_plane(output: Path, relative: str, payload: bytes) -> None:
    path = output / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def cell_mask_and_color(image: IndexedPNG, cell: int, label: str) -> tuple[bytes, int]:
    row, column = divmod(cell, 40)
    colors: set[int] = set()
    scanlines = bytearray()
    for y in range(8):
        pattern = 0
        for x in range(8):
            value = image.pixels[(row * 8 + y) * image.width + column * 8 + x]
            if value:
                colors.add(value)
                pattern |= 0x80 >> x
        scanlines.append(pattern)
    if len(colors) > 1:
        raise ValueError(f"{label}: character cell ({column}, {row}) uses {len(colors)} colors; reduce it to black plus one foreground color")
    return bytes(scanlines), next(iter(colors), 0)


def charset_id_order(source: Path) -> list[bytes]:
    """Load the stable ID contract without retaining a source atlas PNG."""
    payload = json.loads((source / "charset" / "id-order.json").read_text())
    masks = payload.get("glyph_masks_hex")
    if payload.get("format") != "cp64-charset-id-order-v1" or not isinstance(masks, list) or len(masks) != 256:
        raise ValueError("charset/id-order.json: expected 256 glyph masks")
    try:
        ordered = [bytes.fromhex(mask) for mask in masks]
    except ValueError as error:
        raise ValueError("charset/id-order.json: invalid glyph mask encoding") from error
    if any(len(mask) != 8 for mask in ordered) or ordered[0] != bytes(8):
        raise ValueError("charset/id-order.json: expected eight-byte masks with a blank glyph zero")
    return ordered


def compile_character_images(images: dict[str, IndexedPNG], stable_order: list[bytes] | None = None) -> tuple[bytes, dict[str, bytes], dict[str, bytes]]:
    """Derive one shared C64 charset and screen/color maps from rendered images."""
    glyph_ids: dict[bytes, int] = {bytes(8): 0}
    charset = bytearray(2048)
    spare_ids: list[int] = []
    if stable_order is not None:
        for glyph, mask in enumerate(stable_order):
            glyph_ids.setdefault(mask, glyph)
            charset[glyph * 8:glyph * 8 + 8] = mask
        spare_ids = [glyph for glyph, mask in enumerate(stable_order) if glyph_ids[mask] != glyph]
    encoded: dict[str, list[tuple[bytes, int]]] = {}
    for label, image in images.items():
        if (image.width, image.height) != (320, 200):
            raise ValueError(f"{label}: expected a 320×200 character-screen image")
        cells = [cell_mask_and_color(image, cell, label) for cell in range(1000)]
        encoded[label] = cells
    active_masks = {mask for cells in encoded.values() for mask, _ in cells}
    if len(active_masks) > 256:
        raise ValueError(f"shared charset group needs {len(active_masks)} unique glyphs; reduce the screens that share this charset or reduce their unique glyphs")
    for cells in encoded.values():
        for mask, _ in cells:
            if mask not in glyph_ids:
                if stable_order is not None:
                    if not spare_ids:
                        raise ValueError("shared charset group has no free stable glyph IDs; reduce unique glyphs or split screens into a separate charset group")
                    glyph_ids[mask] = spare_ids.pop(0)
                    charset[glyph_ids[mask] * 8:glyph_ids[mask] * 8 + 8] = mask
                else:
                    glyph_ids[mask] = len(glyph_ids)
    if stable_order is None:
        for mask, glyph in glyph_ids.items():
            charset[glyph * 8:glyph * 8 + 8] = mask
    screens = {label: bytes(glyph_ids[mask] for mask, _ in cells) for label, cells in encoded.items()}
    colors = {label: bytes(color for _, color in cells) for label, cells in encoded.items()}
    return bytes(charset), screens, colors


def title_state_image(base: IndexedPNG, selections: dict, state: str) -> IndexedPNG:
    """Move the base title marker and recolor the named selection rows visually."""
    if selections.get("base") != "one" or set(selections.get("states", {})) != set(TITLE_STATES):
        raise ValueError("title/selection.json: expected one base and auto/one/two states")
    marker_column, marker_row = selections["marker"]["source_cell"]
    active, inactive = selections["highlight"]["active_color"], selections["highlight"]["inactive_color"]
    if not (0 <= marker_column < 40 and 0 <= marker_row < 25 and 0 <= active < 16 and 0 <= inactive < 16):
        raise ValueError("title/selection.json: invalid marker or highlight geometry")
    pixels = bytearray(base.pixels)
    def index(column: int, row: int, x: int, y: int) -> int:
        return (row * 8 + y) * 320 + column * 8 + x
    marker = bytes(pixels[index(marker_column, marker_row, x, y)] for y in range(8) for x in range(8))
    for y in range(8):
        for x in range(8):
            pixels[index(marker_column, marker_row, x, y)] = 0
    destination_row = selections["states"][state]["row"]
    if not 0 <= destination_row < 25:
        raise ValueError(f"title/selection.json: invalid {state} row")
    for y in range(8):
        for x in range(8):
            pixels[index(marker_column, destination_row, x, y)] = marker[y * 8 + x]
    for row in {data["row"] for data in selections["states"].values()}:
        if not 0 <= row < 25:
            raise ValueError("title/selection.json: invalid selection row")
        text_start = selections["states"][next(name for name, data in selections["states"].items() if data["row"] == row)]["text_start_column"]
        text_width = selections["states"][next(name for name, data in selections["states"].items() if data["row"] == row)]["text_width"]
        for column in range(text_start, text_start + text_width):
            for y in range(8):
                for x in range(8):
                    address = index(column, row, x, y)
                    if pixels[address]:
                        pixels[address] = active if row == destination_row else inactive
    return IndexedPNG(base.width, base.height, base.palette, bytes(pixels))


def character_images(source: Path) -> dict[str, IndexedPNG]:
    title = read_indexed_png(source / "title/image.png")
    selections = json.loads((source / "title/selection.json").read_text())
    return {**{f"title/{state}": title_state_image(title, selections, state) for state in TITLE_STATES}, "info": read_indexed_png(source / "info/image.png")}


def compile_character_screens(source: Path, output: Path) -> None:
    images = character_images(source)
    charset, screens, colors = compile_character_images(images, charset_id_order(source))
    selections = json.loads((source / "title" / "selection.json").read_text())
    marker_column, marker_row = selections["marker"]["source_cell"]
    marker_cell = marker_row * 40 + marker_column
    marker_color = cell_mask_and_color(read_indexed_png(source / "title" / "image.png"), marker_cell, "title/image.png")[1]
    for state in TITLE_STATES:
        color = bytearray(colors[f"title/{state}"])
        color[marker_cell] = marker_color
        for name, geometry in selections["states"].items():
            row = geometry["row"]
            color[row * 40 + geometry["hotkey_column"]] = selections["highlight"]["active_color"]
            fill = selections["highlight"]["active_color"] if name == state else selections["highlight"]["inactive_color"]
            for column in range(geometry["text_start_column"], geometry["text_start_column"] + geometry["text_width"]):
                color[row * 40 + column] = fill
        destination = selections["states"][state]["row"] * 40 + marker_column
        if state != "one":
            color[destination] = cell_mask_and_color(read_indexed_png(source / "title" / "image.png"), destination, "title/image.png")[1]
        colors[f"title/{state}"] = bytes(color)
    write_plane(output, "charset.bin", charset)
    write_plane(output, "title/one/screen.bin", screens["title/one"])
    write_plane(output, "title/one/color.bin", colors["title/one"])
    write_plane(output, "info/screen.bin", screens["info"])
    write_plane(output, "info/color.bin", colors["info"])


def compile_blank_board(source: Path, output: Path) -> None:
    selectors = require_pixels(source, "game/board/bitmap-selectors.png", 160, 200)
    high = require_pixels(source, "game/board/screen-hi.png", 40, 25)
    low = require_pixels(source, "game/board/screen-lo.png", 40, 25)
    color = require_pixels(source, "game/board/color-lo.png", 40, 25)
    if any(index > 3 for index in selectors):
        raise ValueError("game/board/bitmap-selectors.png: selectors must be 0..3")
    bitmap = bytearray(8000)
    for y in range(200):
        for x in range(160):
            cell = (y // 8) * 40 + x // 4
            bitmap[cell * 8 + y % 8] |= selectors[y * 160 + x] << (6 - 2 * (x % 4))
    write_plane(output, "game/blank/bitmap.bin", bytes(bitmap))
    write_plane(output, "game/blank/screen.bin", bytes((left << 4) | right for left, right in zip(high, low)))
    write_plane(output, "game/blank/color.bin", bytes(color))


def set_selector(bitmap: bytearray, x: int, y: int, selector: int) -> None:
    cell = (y // 8) * 40 + x // 4
    address = cell * 8 + y % 8
    shift = 6 - 2 * (x % 4)
    bitmap[address] = (bitmap[address] & ~(3 << shift)) | (selector << shift)


def exchange_local_selectors(bitmap: bytearray, screen_cell: int) -> None:
    """Swap selectors 01/10 in one bitmap cell without changing its pixels."""
    for scanline in range(8):
        address = screen_cell * 8 + scanline
        pattern = bitmap[address]
        swapped = 0
        for pair in range(4):
            selector = (pattern >> (6 - pair * 2)) & 3
            if selector == 1:
                selector = 2
            elif selector == 2:
                selector = 1
            swapped |= selector << (6 - pair * 2)
        bitmap[address] = swapped


def mark_cell_colors(pixels: bytes, mark: str) -> dict[tuple[int, int], set[int]]:
    """Return native 4×8-cell inks for a 14×24 multicolor mark source."""
    primary = 10 if mark == "x" else 3
    cells: dict[tuple[int, int], set[int]] = {}
    for cell_y in range(3):
        for cell_x in range(4):
            colors = {
                pixels[y * 14 + x]
                for y in range(cell_y * 8, min(cell_y * 8 + 8, 24))
                for x in range(cell_x * 4, min(cell_x * 4 + 4, 14))
                if pixels[y * 14 + x]
            }
            # Selector 01 is the fixed mark primary; selector 11 is one
            # Color-RAM accent per C64 4×8 cell. A cell can therefore use the
            # primary plus one independent accent, not arbitrary global inks.
            if len(colors - {primary}) > 1:
                raise ValueError(
                    f"game/marks/{mark}.png: cell ({cell_x}, {cell_y}) has too many colors; "
                    "use black plus the primary and at most one accent"
                )
            cells[(cell_x, cell_y)] = colors
    if not any(primary in colors for colors in cells.values()):
        raise ValueError(f"game/marks/{mark}.png: primary color must be palette index {primary}")
    return cells


def stamp_mark(source: Path, base: dict[str, bytes], mark: str, cells: str = "abcdefghi") -> dict[str, bytes]:
    pixels = require_pixels(source, f"game/marks/{mark}.png", 14, 24)
    primary = 10 if mark == "x" else 3
    source_cells = mark_cell_colors(pixels, mark)
    bitmap = bytearray(base["bitmap"])
    blank_screen = base["screen"]
    screen = bytearray(blank_screen)
    color_ram = bytearray(base["color"])
    coordinates = json.loads((source / "game/board/layout.json").read_text())["cell_rectangles"]
    remapped_cells: set[int] = set()
    for cell in cells:
        physical_x, physical_y, width, height = coordinates[cell]["preview_xywh"]
        if (width, height) != (28, 24):
            raise ValueError("board cell preview rectangles must stay 28×24")
        for y in range(24):
            for x in range(14):
                pixel = pixels[y * 14 + x]
                if pixel == 0:
                    continue
                logical_x = physical_x // 2 + x
                logical_y = physical_y + y
                screen_cell = (logical_y // 8) * 40 + logical_x // 4
                accent = next(iter(source_cells[(x // 4, y // 8)] - {primary}), 0)
                original = blank_screen[screen_cell]
                if screen_cell not in remapped_cells and original >> 4 and not (original & 0x0f):
                    # A grid line already owns selector 01. Move it to 10 so
                    # the mark can use 01 and keep the supplied pixels intact.
                    exchange_local_selectors(bitmap, screen_cell)
                    screen[screen_cell] = (primary << 4) | (original >> 4)
                    remapped_cells.add(screen_cell)
                elif screen_cell not in remapped_cells:
                    screen[screen_cell] = (primary << 4) | (original & 0x0f)
                    remapped_cells.add(screen_cell)
                if accent:
                    color_ram[screen_cell] = accent
                if pixel == accent and accent:
                    set_selector(bitmap, logical_x, logical_y, 3)
                else:
                    set_selector(bitmap, logical_x, logical_y, 1)
    return {"bitmap": bytes(bitmap), "screen": bytes(screen), "color": bytes(color_ram)}


def validate_reference(reference: dict, relative: str, payload: bytes) -> None:
    expected = reference[relative]
    if len(payload) != expected["bytes"] or hashlib.sha256(payload).hexdigest() != expected["sha256"]:
        raise ValueError(f"reference plane mismatch: {relative}")


ENTRY_PLANES = {
    "charset": "charset.bin",
    "title_screen": "title/one/screen.bin",
    "title_color": "title/one/color.bin",
    "info_screen": "info/screen.bin",
    "info_color": "info/color.bin",
    "board_bitmap": "game/blank/bitmap.bin",
    "board_screen": "game/blank/screen.bin",
    "board_color": "game/blank/color.bin",
}


def validate_sources(source: Path) -> dict:
    provenance = json.loads((source / "provenance.json").read_text(encoding="utf-8"))
    required = set(SOURCE_PNGS) | {
        "title/selection.json", "charset/id-order.json", "game/board/layout.json", "cp64-manifest.json",
    }
    if set(provenance["sources"]) != required:
        raise ValueError("source integrity: incorrect original-source inventory")
    for relative in sorted(required):
        expected = provenance["sources"][relative]
        try:
            payload = (source / relative).read_bytes()
        except OSError as error:
            raise ValueError(f"source integrity: missing {relative}") from error
        if len(payload) != expected["bytes"] or hashlib.sha256(payload).hexdigest() != expected["sha256"]:
            raise ValueError(f"source integrity: changed {relative}")
    return provenance


def compile_assets(output: Path = OUTPUT) -> tuple[dict[str, Path], dict]:
    """Return ({logical_name: generated_path}, JSON-compatible metadata)."""
    output = Path(output)
    provenance = validate_sources(ASSETS)
    compile_character_screens(ASSETS, output)
    compile_blank_board(ASSETS, output)
    paths = {name: output / relative for name, relative in ENTRY_PLANES.items()}
    reference = json.loads((ASSETS / "cp64-manifest.json").read_text())["generated_bins"]
    for name, relative in ENTRY_PLANES.items():
        validate_reference(reference, relative, paths[name].read_bytes())
    packed = bytearray()
    metadata = {
        "format": "falken9-graphics-v1",
        "source_provenance": {
            "path": "assets/game-art/provenance.json",
            "sha256": hashlib.sha256((ASSETS / "provenance.json").read_bytes()).hexdigest(),
            "upstream_commit": provenance["upstream_commit"],
        },
        "vic": {
            "bank_base": 0, "dd00_low_bits": 3, "background": 0, "border": 0,
            "title": {"d011": 0x1b, "d016": 0x08, "d018": 0x1c,
                      "copies": {"charset": 0x3000, "title_screen": 0x0400, "title_color": 0xd800}},
            "info": {"d011": 0x1b, "d016": 0x08, "d018": 0x1c,
                     "copies": {"charset": 0x3000, "info_screen": 0x0400, "info_color": 0xd800}},
            "game": {"d011": 0x3b, "d016": 0x18, "d018": 0x18,
                     "copies": {"board_bitmap": 0x2000, "board_screen": 0x0400, "board_color": 0xd800}},
        },
        "regions": {}, "cells": {},
    }

    def add_region(name: str, payload: bytes) -> str:
        metadata["regions"][name] = {
            "offset": len(packed), "length": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        packed.extend(payload)
        return name

    for name, path in paths.items():
        add_region(name, path.read_bytes())
    base = {p: paths[f"board_{p}"].read_bytes() for p in ("bitmap", "screen", "color")}
    for mark in "xo":
        for plane, payload in stamp_mark(ASSETS, base, mark).items():
            validate_reference(reference, f"game/all-{mark}/{plane}.bin", payload)
    bases = {"bitmap": 0x2000, "screen": 0x0400, "color": 0xd800}
    for square, cell in enumerate("abcdefghi", 1):
        marks = {mark: stamp_mark(ASSETS, base, mark, cell) for mark in "xo"}
        descriptor = {"square": square, "planes": {}}
        for plane, blank in base.items():
            # Exact-difference crops deliberately exclude shared empty rows.
            # The old 4x4 attribute crop could repaint the adjacent cell.
            offsets = [i for i, value in enumerate(blank)
                       if any(marks[mark][plane][i] != value for mark in "xo")]
            offsets_name = add_region(f"cell_{cell}_{plane}_offsets", b"".join(
                offset.to_bytes(2, "little") for offset in offsets))
            values = {mark: add_region(f"cell_{cell}_{mark}_{plane}", bytes(
                marks[mark][plane][offset] for offset in offsets)) for mark in "xo"}
            descriptor["planes"][plane] = {
                "destination_base": bases[plane], "destination_offsets": offsets,
                "offsets_region": offsets_name, "values": values,
            }
        metadata["cells"][cell] = descriptor
    metadata["packed"] = {"length": len(packed), "sha256": hashlib.sha256(packed).hexdigest()}
    paths["packed"] = output / "graphics.bin"
    paths["metadata"] = output / "graphics.json"
    paths["packed"].write_bytes(packed)
    # Preserve insertion order: the region order documents contiguous packing.
    paths["metadata"].write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return paths, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    paths, metadata = compile_assets(args.output)
    print(json.dumps({"paths": {name: str(path) for name, path in paths.items()}, "metadata": metadata}, sort_keys=True))


if __name__ == "__main__":
    main()
