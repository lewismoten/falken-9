"""Prepare a Vorbis transport from actual VICE PCM, never host synthesis."""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

ACCEPTED_PRG_SHA256 = 'c571353a61c8a663050c33809b6ca880d29aebc969c545a717da2644eed3143a'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pcm_metrics(raw):
    samples = array.array('h', raw)
    if sys.byteorder != 'little':
        samples.byteswap()
    if not samples:
        raise ValueError('empty PCM')
    return dict(samples=len(samples), nonzero_samples=sum(x != 0 for x in samples),
                clipped_samples=sum(x <= -32768 or x >= 32767 for x in samples),
                peak=max(map(abs, samples)),
                rms=math.sqrt(sum(x*x for x in samples)/len(samples)))


def inspect_audio(path):
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))
    streams = probe['streams']
    if len(streams) != 1 or streams[0]['codec_type'] != 'audio':
        raise ValueError('expected one audio stream')
    stream = streams[0]
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-xerror', '-i', str(path),
                                   '-map', '0:a:0', '-f', 's16le', '-c:a', 'pcm_s16le', '-'])
    metrics = pcm_metrics(raw)
    rate, channels = int(stream['sample_rate']), stream['channels']
    return dict(codec=stream['codec_name'], container=probe['format']['format_name'],
                sample_rate=rate, channels=channels,
                duration_seconds=float(probe['format']['duration']),
                decoded_frames=metrics['samples']//channels,
                decoded_duration_seconds=metrics['samples']/channels/rate,
                bytes=Path(path).stat().st_size, sha256=sha256(path), pcm_s16le=metrics)


def convert(source, destination, *, start=0.0, duration=38.0):
    source, destination = Path(source), Path(destination)
    if start < 0 or duration <= 1:
        raise ValueError('invalid excerpt boundary')
    original = inspect_audio(source)
    if original['codec'] != 'pcm_s16le' or original['duration_seconds'] < start+duration:
        raise ValueError('expected sufficient actual PCM WAV')
    if original['pcm_s16le']['rms'] == 0 or original['pcm_s16le']['clipped_samples']:
        raise ValueError('silent or clipped source capture')
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-y', '-i', str(source),
                    '-ss', str(start), '-t', str(duration), '-map_metadata', '-1',
                    '-af', f'afade=t=in:st=0:d=0.05,afade=t=out:st={duration-1}:d=1',
                    '-c:a', 'libvorbis', '-q:a', '5', '-flags:a', '+bitexact',
                    '-fflags', '+bitexact', '-metadata', 'title=Patient Calculations',
                    '-metadata', 'artist=Mercury Quill / Lewis Moten project',
                    '-metadata', 'comment=Original Falken-9 game score; native VICE capture, not physical SID',
                    str(destination)], check=True)
    result = inspect_audio(destination)
    if result['codec'] != 'vorbis' or result['container'] != 'ogg':
        raise ValueError('not Ogg/Vorbis')
    if abs(result['duration_seconds']-duration) > 0.05 or result['pcm_s16le']['rms'] <= 0:
        raise ValueError('bad duration or silence')
    if result['pcm_s16le']['clipped_samples']:
        raise ValueError('clipped encoded audio')
    return dict(source=original, output=result,
                conversion=dict(start_seconds=start, duration_seconds=duration,
                                encoder='libvorbis', quality=5, gain_normalization=False,
                                fade_in_seconds=0.05, fade_out_seconds=1.0),
                ffmpeg_version=subprocess.check_output(['ffmpeg', '-version'], text=True).splitlines()[0])


def capture(build_path, output):
    """Run the exact frozen PRG at its title with no injected keys/events."""
    from scripts.verify_graphical_stock_rom import Vice, DEFAULT_VICE_ROOT
    built = json.loads(Path(build_path).read_text())
    if sha256(built['prg_path']) != ACCEPTED_PRG_SHA256:
        raise ValueError('not the accepted010 PRG')
    out = Path(output).resolve()
    v = Vice(built, built['prg_path'], out, DEFAULT_VICE_ROOT, audio_output='wav')
    try:
        assert v.value('view') == 0 and v.value('audio_ntsc') == 0
        v.command('warp off')
        v.command('disable 1'); v.command('disable 2')
        v.command(f"break {v.labels['audio_tick']:04x}")
        v.command('x')
        begin = v.command('r')
        v.command(f"trace exec {v.labels['audio_event']:04x} {v.labels['audio_event']:04x}")
        v.command('trace store d412 d412')
        v.command('ignore 4 '+format(2100-1, 'x'))
        v.command('x')
        assert v.registers()[0] == v.labels['audio_tick']
        end = v.command('r')
        assert v.value('view') == 0 and v.value('audio_pending') == 0
        assert v.value('audio_sfx_left') == 0 and v.memory(0xd412) == b'\0'
        info = dict(prg_sha256=sha256(built['prg_path']), timing='PAL',
                    title_only=True, injected_keys=0, injected_events=0,
                    raster_ticks=2100, begin_registers=begin, end_registers=end)
    finally:
        v.close()
    log = (out/'monitor.log').read_text()
    if '(Trace exec ' in log or '(Trace store ' in log:
        raise ValueError('unexpected event or voice-three gate write')
    info.update(wav_sha256=sha256(out/'sid.wav'), monitor_sha256=sha256(out/'monitor.log'),
                vice_executable_sha256=sha256(DEFAULT_VICE_ROOT/'usr/bin/x64'))
    (out/'capture.json').write_text(json.dumps(info, indent=2)+'\n')
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--capture-build', action='store_true', help='source is build.json; destination is private capture directory')
    parser.add_argument('--start', type=float, default=0.0)
    parser.add_argument('--duration', type=float, default=38.0)
    args = parser.parse_args()
    result = capture(args.source, args.destination) if args.capture_build else convert(
        args.source, args.destination, start=args.start, duration=args.duration)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
