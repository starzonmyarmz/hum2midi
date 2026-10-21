import os
import subprocess
import tempfile

import numpy as np

SR = 22050
HOP = 256


def decode(path, wav):
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", f"LEI16@{SR}", "-c", "1", path, wav],
        check=True,
        capture_output=True,
    )


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
    ok = voiced & ~np.isnan(f0)
    midi = np.full_like(f0, np.nan)
    midi[ok] = librosa.hz_to_midi(f0[ok])

    smooth = midi.copy()
    for i in range(len(smooth)):
        w = midi[max(0, i - 3) : i + 4]
        w = w[~np.isnan(w)]
        if ok[i] and len(w):
            smooth[i] = np.median(w)

    segments, cur = [], None
    for i, p in enumerate(smooth):
        if np.isnan(p):
            if cur:
                segments.append(cur)
                cur = None
        elif cur and abs(p - np.median(cur["ps"])) < 0.75:
            cur["ps"].append(p)
            cur["end"] = t[i]
        else:
            if cur:
                segments.append(cur)
            cur = {"ps": [p], "start": t[i], "end": t[i]}
    if cur:
        segments.append(cur)

    hop_s = HOP / SR
    notes = [
        {"pitch": int(round(np.median(s["ps"]))), "start": s["start"], "end": s["end"] + hop_s}
        for s in segments
        if s["end"] - s["start"] >= 0.08
    ]

    merged = []
    for n in notes:
        if merged and merged[-1]["pitch"] == n["pitch"] and n["start"] - merged[-1]["end"] < 0.06:
            merged[-1]["end"] = n["end"]
        else:
            merged.append(n)
    return merged


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


def transcribe(src, out, bpm=None, fold=False):
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

    grid = 60 / bpm / 4
    t0 = notes[0]["start"]
    pm = pretty_midi.PrettyMIDI(initial_tempo=float(bpm))
    inst = pretty_midi.Instrument(program=0, name="Hum")
    prev_end = 0
    for n in notes:
        s_idx = round((n["start"] - t0) / grid)
        start = max(s_idx * grid, prev_end)
        end = max(round((n["end"] - t0) / grid), s_idx + 1) * grid
        if end > start:
            inst.notes.append(pretty_midi.Note(velocity=90, pitch=n["pitch"], start=start, end=end))
            prev_end = end
    pm.instruments.append(inst)
    pm.write(out)
    return bpm, len(inst.notes)
