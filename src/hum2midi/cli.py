import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor

from . import __version__

DEFAULT_OUT_DIRNAME = "midi"
AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".aif", ".aiff", ".aac", ".flac", ".ogg", ".opus", ".caf", ".mp4"}


def _expand(paths):
    for path in paths:
        if os.path.isdir(path):
            for name in sorted(os.listdir(path)):
                if os.path.splitext(name)[1].lower() in AUDIO_EXTS:
                    yield os.path.join(path, name)
        else:
            yield path


def _job(args):
    src, out, bpm, fold, quantize = args
    from .core import transcribe

    try:
        return src, transcribe(src, out, bpm=bpm, fold=fold, quantize=quantize), None
    except Exception as e:
        return src, None, str(e)


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="hum2midi",
        description="Convert hummed or monophonic audio recordings to quantized MIDI.",
    )
    p.add_argument("files", nargs="+", help="audio files or folders of audio files (m4a, wav, mp3, aiff, ...)")
    p.add_argument("-o", "--out", help=f'output folder (default: "{DEFAULT_OUT_DIRNAME}" folder next to each input)')
    p.add_argument("-b", "--bpm", type=int, help="use this tempo instead of estimating it")
    p.add_argument("-f", "--fold", action="store_true", help="fold stray notes into one octave range")
    p.add_argument("-q", "--quantize", action=argparse.BooleanOptionalAction, default=False, help="quantize notes to grid (default: off)")
    p.add_argument("-j", "--jobs", type=int, default=os.cpu_count(), help="parallel workers")
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    a = p.parse_args(argv)

    files = list(_expand(a.files))
    if not files:
        p.error("no audio files found")

    jobs = []
    for f in files:
        out_dir = os.path.expanduser(a.out) if a.out else os.path.join(os.path.dirname(os.path.abspath(f)), DEFAULT_OUT_DIRNAME)
        base = os.path.splitext(os.path.basename(f))[0]
        jobs.append((f, os.path.join(out_dir, base + ".mid"), a.bpm, a.fold, a.quantize))

    failed = 0
    written = []
    with ProcessPoolExecutor(max_workers=max(1, min(a.jobs, len(jobs)))) as ex:
        for job, (src, res, err) in zip(jobs, ex.map(_job, jobs)):
            name = os.path.basename(src)
            if err:
                failed += 1
                print(f"{name}: error: {err}", file=sys.stderr)
            elif res is None:
                failed += 1
                print(f"{name}: no notes found", file=sys.stderr)
            else:
                print(f"{name}: {res[0]} BPM, {res[1]} notes")
                written.append(os.path.dirname(job[1]))
    for d in dict.fromkeys(written):
        print(f"Wrote MIDI to {d}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
