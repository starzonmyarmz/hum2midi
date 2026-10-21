import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor

from . import __version__

DEFAULT_OUT = "~/Desktop/Hum MIDI"


def _job(args):
    src, out, bpm, fold = args
    from .core import transcribe

    try:
        return src, transcribe(src, out, bpm=bpm, fold=fold), None
    except Exception as e:
        return src, None, str(e)


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="hum2midi",
        description="Convert hummed or monophonic audio recordings to quantized MIDI.",
    )
    p.add_argument("files", nargs="+", help="audio files (m4a, wav, mp3, aiff, ...)")
    p.add_argument("-o", "--out", default=DEFAULT_OUT, help=f"output folder (default: {DEFAULT_OUT})")
    p.add_argument("-b", "--bpm", type=int, help="use this tempo instead of estimating it")
    p.add_argument("-f", "--fold", action="store_true", help="fold stray notes into one octave range")
    p.add_argument("-j", "--jobs", type=int, default=os.cpu_count(), help="parallel workers")
    p.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    a = p.parse_args(argv)

    out_dir = os.path.expanduser(a.out)
    os.makedirs(out_dir, exist_ok=True)

    jobs = []
    for f in a.files:
        base = os.path.splitext(os.path.basename(f))[0]
        jobs.append((f, os.path.join(out_dir, base + ".mid"), a.bpm, a.fold))

    failed = 0
    with ProcessPoolExecutor(max_workers=max(1, min(a.jobs, len(jobs)))) as ex:
        for src, res, err in ex.map(_job, jobs):
            name = os.path.basename(src)
            if err:
                failed += 1
                print(f"{name}: error: {err}", file=sys.stderr)
            elif res is None:
                failed += 1
                print(f"{name}: no notes found", file=sys.stderr)
            else:
                print(f"{name}: {res[0]} BPM, {res[1]} notes")
    print(f"Wrote MIDI to {out_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
