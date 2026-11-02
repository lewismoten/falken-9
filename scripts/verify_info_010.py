"""Verify every INFO scroll on exact PRG/D64 under stock-ROM VICE."""
from pathlib import Path
import hashlib
import json
from scripts.verify_graphical_stock_rom import Vice, DEFAULT_VICE_ROOT


def verify(built, image, output):
    out = Path(output).resolve()
    v = Vice(built, image, out, DEFAULT_VICE_ROOT)
    raw = Path(built['path']).read_bytes()
    start = built['labels']['info_chars'] - built['load']
    end = built['labels']['info_line_colors'] - built['load']
    count = (end-start)//29
    frame = Path(built['path']).parent.joinpath('info_screen.bin').read_bytes()
    colors = Path(built['path']).parent.joinpath('info_color.bin').read_bytes()
    body = {r*40+c for r in range(4,22) for c in range(5,34)}
    track = {r*40+34 for r in range(4,22)}
    pages = []
    try:
        title = v.memory(0x400,1000)
        v.capture('title')
        v.key('I')
        for scroll in range(count-17):
            assert v.value('info_scroll') == scroll
            screen = v.memory(0x400,1000)
            color = bytes(x & 15 for x in v.memory(0xd800,1000))
            for row in range(18):
                at = (row+4)*40+5
                expected = raw[start+(scroll+row)*29:start+(scroll+row+1)*29]
                assert screen[at:at+29] == expected, (scroll,row)
                assert color[at:at+29] == bytes([raw[end+scroll+row]])*29
            assert all(screen[i] == frame[i] and color[i] == colors[i] for i in range(1000) if i not in body|track)
            pages.append(dict(scroll=scroll,screen_sha256=hashlib.sha256(screen).hexdigest(),color_sha256=hashlib.sha256(color).hexdigest()))
            if scroll in {0,12,26,35,43,count-18}:
                v.capture('info-'+str(scroll).zfill(2))
            v.key(0x11)
        assert v.value('info_scroll') == count-18
        for _ in range(count):v.key(0x91)
        assert v.value('info_scroll') == 0
        v.key('Q');assert v.memory(0x400,1000) == title
        v.key('2');v.key('5');v.key('R');v.key('Q')
        replay_title = v.memory(0x400,1000)
        v.key('I')
        assert v.value('info_scroll') == 0
        v.capture('info-after-replay')
        v.key('Q');assert v.memory(0x400,1000) == replay_title
        result = dict(status='passed',scope='stock-ROM VICE, actual framebuffer and monitor KERNAL queue input; not physical/browser keys',prg_sha256=built['prg_sha256'],image_sha256=hashlib.sha256(Path(image).read_bytes()).hexdigest(),line_count=count,all_offsets=count-17,pages=pages,template_preserved=True,white_body_yellow_headings=True,up_down_clamps=True,replay_info_title_roundtrip=True,screenshots={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.png')})
        (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    finally:
        v.close()


if __name__ == '__main__':
    import sys
    b=json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(verify(b,sys.argv[2],sys.argv[3]),indent=2))
