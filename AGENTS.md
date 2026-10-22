# hum2midi - Agent Instructions

## Project Overview
Convert hummed or monophonic audio recordings to quantized MIDI. Cross-platform (requires ffmpeg).

## Key Files
- `src/hum2midi/cli.py` — CLI entry point, argument parsing, parallel processing
- `src/hum2midi/core.py` — Audio decode (ffmpeg), pitch tracking, quantization, MIDI output
- `pyproject.toml` — Package metadata, dependencies, entry point

## Development Commands
```bash
# Install in development mode
pip install -e .

# Run CLI
hum2midi --help
hum2midi input.m4a -q -b 120 -f

# Run tests (manual verification)
hum2midi --version
```

## Architecture Notes
- **Audio decode**: Uses ffmpeg via subprocess (all platforms). Sample rate 22050 Hz, mono, 16-bit.
- **Pitch tracking**: librosa PYIN (C2–C6), RMS-based onset detection
- **Quantization**: Optional (`-q` flag). Snaps note onsets to 16th-note grid, aligns phase to first note.
- **Tempo estimation**: Grid search 60–180 BPM + librosa onset strength refinement
- **Octave folding**: `-f` folds stray notes into median octave ±6 semitones

## Coding Conventions
- Minimal comments; rationale in commit messages
- Type hints not required but welcome
- Keep core logic in `core.py`, CLI thin in `cli.py`
- Subprocess calls use `check=True, capture_output=True`

## Release Process
Use `scripts/release.sh <patch|minor|major|X.Y.Z>`; don't bump, tag, or edit the formula by hand.
- Prereqs: on `main`, clean working tree (commit changes first), `gh` authenticated, tap checked out at `~/Code/homebrew-tap` (override with `TAP_DIR`).
- It bumps `pyproject.toml`, commits, tags `vX.Y.Z`, pushes, creates the GitHub release with generated notes, then updates the tag in the tap's `Formula/hum2midi.rb` and pushes it.
- It prompts for confirmation before changing anything. Releasing is outward-facing: only run it when the user asks.
