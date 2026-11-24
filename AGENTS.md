# hum2midi

Convert hummed or monophonic audio recordings to quantized MIDI

## Commands

```sh
python3 -m venv .venv && .venv/bin/pip install -e . pytest   # once
.venv/bin/pytest                                            # the tests
.venv/bin/hum2midi input.m4a -q -b 120 -f                   # try it (needs ffmpeg)
uvx ruff check . && uvx ruff format --check .               # lint and formatting, as CI runs them
scripts/release --dry-run                                   # what the next release would be
```

## Layout

- `pyproject.toml`: the package metadata, dependencies and entry points. The version lives in `[project] version`.
- `src/hum2midi/`: the package. `__version__` comes from the installed package's metadata, never a literal.
  - `cli.py`: the `hum2midi` command: argument parsing and parallel processing across input files.
  - `core.py`: everything else:
    - **Audio decode**: ffmpeg through `subprocess`, to 22050 Hz mono 16-bit.
    - **Pitch tracking**: librosa PYIN over C2–C6, with RMS-based onset detection.
    - **Quantization** (`-q`): snaps note onsets to a 16th-note grid, phase-aligned to the first note.
    - **Tempo estimation**: grid search over 60–180 BPM, refined with librosa's onset strength.
    - **Octave folding** (`-f`): folds stray notes into the median octave ±6 semitones.
- `tests/`: pytest tests. `test_version.py` checks `__version__` against `pyproject.toml`.
- `packaging/homebrew/hum2midi.rb`: the formula template `starzonmyarmz/homebrew-tap` renders from each release.
- `packaging/icon.svg`: the icon in the README heading, the same one iamdanielmarino.com shows.
- `.python-version`: the Python CI runs.
- `.github/workflows/itch.yml`: on each `v*` tag, pushes a source zip to itch.io's `source` channel (needs the `BUTLER_API_KEY` secret).
- `scripts/`: release tooling (`release`, `version.sh`, `changelog-notes`, `check-changelog`).

## Invariants and footguns

What was learned the hard way. Add to this list whenever something breaks in a way the code doesn't make obvious.

- The version lives only in `pyproject.toml`. Read it at runtime with `importlib.metadata.version("hum2midi")`; a literal `__version__` goes stale at the next release.
- Don't bump the version by hand. It only changes at release.
- Tags are always `v` + the exact version. A tag without the `v` never triggers the release workflow.
- ffmpeg is a runtime dependency on every platform: decoding shells out to it. Run subprocesses with `check=True, capture_output=True`.
- Keep the logic in `core.py` and `cli.py` thin.
- The Homebrew formula is `packaging/homebrew/hum2midi.rb`, a template the tap renders from `main` and the latest release's tag. Edit it here, never in the tap.

## Conventions

- Conventional Commits with Title-Case scopes: `feat(Engine): …`. The body explains why.
- Tests ship in the same commit as the change. Pure logic is tested; the UI or host shell stays thin.
- A `feat`, `fix` or `perf` commit that someone using hum2midi would notice adds a line under `## [Unreleased]` in `CHANGELOG.md`, in the same commit, written for them, not as a code summary.
- This repo is public. Keep real names, logins, paths and work data out of code, fixtures, docs, the changelog and commits.
- Breaking means changed command-line flags or output, or a removed or renamed public function.
- Minimal comments; rationale goes in commit messages. Type hints are welcome but not required.

## Releasing

Releases happen only when asked. Never bump, tag or publish on your own.

`scripts/release` works out the bump from commits since the last tag, finalizes the changelog, commits `chore(Release): X.Y.Z`, tags `vX.Y.Z` and pushes. The tag triggers `.github/workflows/release.yml`.
