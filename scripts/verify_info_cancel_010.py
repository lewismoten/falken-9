"""Final D64: real matrix cancel -> full INFO -> title/replay recovery."""
from pathlib import Path
import hashlib,json
from scripts.verify_quit_keys import KeyVice
from scripts.verify_graphical_stock_rom import DEFAULT_VICE_ROOT


def verify(built,image,output):
    out=Path(output).resolve();v=KeyVice(built,image,out,DEFAULT_VICE_ROOT)
    try:
        v.setup_keys();title=v.memory(0x400,1000)
        v.command('delete');v.command(f"break {v.labels['graph_board_attention']:04x}")
        v.event('0',True);v.steps(100000);v.event('0',False)
        if v.registers()[0]!=v.labels['graph_board_attention']:v.command('x')
        v.command('delete');v.command(f"watch store {v.labels['quit_pending']:04x}")
        v.event('q',True);v.command('x');assert v.value('quit_pending')==128
        v.event('q',False);v.until('input_wait',forbid_commit=True)
        v.command('delete');v.steps(100000)
        assert v.value('view')==0 and v.value('history_length')==0 and v.value('move_result')==0
        # Following INFO commands use the real foreground GETIN dispatch stack;
        # only cancellation above is XTest/CIA matrix input.
        v.until('input_wait')
        def key(value):
            value=ord(value) if isinstance(value,str) else value
            v.command(f'> 0277 {value:02x}');v.command('> 00c6 01');v.command('x')
            assert v.registers()[0]==v.labels['input_wait']
        key('I');assert v.value('view')==1
        raw=Path(built['path']).read_bytes();start=v.labels['info_chars']-built['load'];end=v.labels['info_line_colors']-built['load'];count=(end-start)//29
        screens=[]
        for scroll in range(count-17):
            assert v.value('info_scroll')==scroll
            screen=v.memory(0x400,1000)
            for row in range(18):assert screen[(row+4)*40+5:(row+4)*40+34]==raw[start+(scroll+row)*29:start+(scroll+row+1)*29]
            screens.append(hashlib.sha256(screen).hexdigest())
            if scroll in {0,43,50}:
                v.command('disable 1');v.steps(30000);v.command(f'screenshot "{out/f"cancel-info-{scroll:02}.png"}" 2')
                v.command('enable 1');v.command('x')
            key(0x11)
        key('Q');assert v.value('view')==0
        key('2');key('5');key('R');key('Q');key('I');assert v.value('info_scroll')==0
        screen=v.memory(0x400,1000);assert hashlib.sha256(screen).hexdigest()==screens[0]
        key('Q');assert v.value('view')==0
        r=dict(status='passed',prg_sha256=built['prg_sha256'],image_sha256=hashlib.sha256(Path(image).read_bytes()).hexdigest(),real_matrix_cancel=True,no_post_cancel_mark=True,all_info_offsets_after_cancel=len(screens),screen_sha256=screens,replay_info_same=True,events=v.events,scope='Stock-ROM true1541 D64 VICE; cancel XTest down/up/CIA, subsequent INFO scroll keys monitor queue; not browser/physical hardware')
        (out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');return r
    finally:v.close()


if __name__=='__main__':
    import sys
    b=json.loads(Path(sys.argv[1]).read_text());print(json.dumps(verify(b,sys.argv[2],sys.argv[3]),indent=2))
