import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

FFMPEG_INSTALL = {
    "darwin": "brew install ffmpeg",
    "win32": "winget install ffmpeg",
    "linux": "sudo apt install ffmpeg",
}

SR = 22050
HOP = 256


def decode(path, wav):
    """Decode audio file to WAV using ffmpeg."""
    if shutil.which("ffmpeg") is None:
        hint = FFMPEG_INSTALL.get(sys.platform, "see https://ffmpeg.org/download.html")
        raise RuntimeError(f"ffmpeg not found on PATH; install it with: {hint}")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", path, "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", wav],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        lines = e.stderr.strip().splitlines()
        raise RuntimeError(f"ffmpeg could not decode this file: {lines[-1] if lines else 'unknown error'}") from e


def pitch_spans(midi, a, b, thr=0.8, min_run=5):
    cuts, run, pend, first = [a], [], [], a
    for i in range(a, b):
        v = midi[i]
        if np.isnan(v):
            continue
        if run and abs(v - np.median(run)) > thr:
            if pend and abs(v - np.median(pend)) > thr:
                pend = []
            if not pend:
                first = i
            pend.append(v)
            if len(pend) >= min_run:
                cuts.append(first)
                run, pend = pend, []
        else:
            run.append(v)
            pend = []
    cuts.append(b)
    return list(zip(cuts, cuts[1:]))


def track_notes(y):
    import librosa

    f0, voiced, _ = librosa.pyin(
        y,
        fmin=librosa.note_to_hz("C2"),
        fmax=librosa.note_to_hz("C6"),
        sr=SR,
        frame_length=2048,
        hop_length=HOP,
    )
    t = librosa.times_like(f0, sr=SR, hop_length=HOP)
    midi = np.where(np.isnan(f0), np.nan, librosa.hz_to_midi(np.where(np.isnan(f0), 1.0, f0)))

    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=HOP)[0][: len(t)]
    db = 20 * np.log10(rms + 1e-6)
    peak = np.percentile(db, 95)
    hi, lo = peak - 22, peak - 30
    on = np.zeros(len(db), bool)
    state = False
    for i, d in enumerate(db):
        state = d > lo if state else d > hi
        on[i] = state

    hop_s = HOP / SR
    regions, i = [], 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]:
                j += 1
            regions.append((i, j))
            i = j
        else:
            i += 1

    from scipy.signal import find_peaks

    notes = []
    for a, b in regions:
        cuts = [a]
        if b - a > 6:
            valleys, _ = find_peaks(-db[a:b], prominence=6)
            cuts += [a + v for v in valleys]
        cuts.append(b)
        for e0, e1 in zip(cuts, cuts[1:]):
            for c0, c1 in pitch_spans(midi, e0, e1):
                if (c1 - c0) * hop_s < 0.06:
                    continue
                seg = midi[c0:c1]
                voiced = seg[~np.isnan(seg)]
                if len(voiced) < 3:
                    continue
                core = voiced[len(voiced) // 4 :] if len(voiced) >= 8 else voiced
                last_voiced = c0 + np.flatnonzero(~np.isnan(seg))[-1]
                d = db[c0:c1]
                loud = np.flatnonzero(d > d.max() - 12)
                live = np.flatnonzero(d > d.max() - 20)
                notes.append(
                    {
                        "pitch": int(round(np.median(core))),
                        "start": t[c0 + loud[0]],
                        "end": min(t[c0 + live[-1]], t[last_voiced]) + hop_s,
                    }
                )
    return notes


def estimate_bpm(y, notes):
    import librosa

    onsets = np.array([n["start"] for n in notes])
    onsets -= onsets[0]
    best = None
    for bpm in np.arange(60, 181, 0.5):
        g = 60 / bpm / 4
        score = np.abs(onsets / g - np.round(onsets / g)).mean() + (0 if 80 <= bpm <= 140 else 0.03)
        if best is None or score < best[0]:
            best = (score, bpm)
    bpm = best[1]

    env = librosa.onset.onset_strength(y=y, sr=SR)
    ref = float(np.atleast_1d(librosa.feature.tempo(onset_envelope=env, sr=SR))[0])
    for c in (bpm, bpm * 2, bpm / 2):
        if 70 <= c <= 160 and abs(c - ref) < abs(bpm - ref) and abs(c - ref) / ref < 0.06:
            bpm = c
    return int(round(bpm))


def fold_octaves(notes):
    center = np.median([n["pitch"] for n in notes])
    for n in notes:
        while n["pitch"] - center > 6:
            n["pitch"] -= 12
        while center - n["pitch"] > 6:
            n["pitch"] += 12


def transcribe(src, out, bpm=None, fold=False, quantize=False):
    import librosa
    import pretty_midi
    import scipy.signal as sg

    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "in.wav")
        decode(src, wav)
        y, _ = librosa.load(wav, sr=SR, mono=True)

    y, _ = librosa.effects.trim(y, top_db=35)
    y = sg.sosfilt(sg.butter(4, 70, "hp", fs=SR, output="sos"), y)

    notes = track_notes(y)
    if len(notes) < 2:
        return None
    if fold:
        fold_octaves(notes)
    bpm = bpm or estimate_bpm(y, notes)

    if quantize:
        grid = 60 / bpm / 4
        starts = np.array([n["start"] for n in notes])
        ang = np.angle(np.exp(2j * np.pi * starts / grid).mean())
        phase = (ang / (2 * np.pi)) * grid
        t0 = phase + round((starts[0] - phase) / grid) * grid
    else:
        t0 = notes[0]["start"]

    pm = pretty_midi.PrettyMIDI(initial_tempo=float(bpm))
    inst = pretty_midi.Instrument(program=0, name="Hum")
    prev_end = 0
    for n in notes:
        if quantize:
            grid = 60 / bpm / 4
            s_idx = round((n["start"] - t0) / grid)
            start = max(s_idx * grid, prev_end)
            end = max(round((n["end"] - t0) / grid), s_idx + 1) * grid
        else:
            start = n["start"]
            end = n["end"]
        if end > start:
            inst.notes.append(pretty_midi.Note(velocity=90, pitch=n["pitch"], start=start, end=end))
            prev_end = end
    pm.instruments.append(inst)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    pm.write(out)
    return bpm, len(inst.notes)
