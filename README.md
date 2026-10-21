# hum2midi

Convert hummed or monophonic audio recordings to quantized MIDI. macOS only (decodes with `afconvert`).

    hum2midi ~/Downloads/*.m4a
    hum2midi -b 100 -f -o ~/Desktop/Songs idea.m4a

Options: `-o` output folder, `-b` fixed tempo, `-f` fold stray octave jumps, `-j` workers.

Install with Homebrew:

    brew install starzonmyarmz/tap/hum2midi

Or from source: `python3 -m venv venv && venv/bin/pip install -e . && ln -s "$PWD/venv/bin/hum2midi" ~/.local/bin/hum2midi`

## Contributors

- Daniel Marino
- Claude (Anthropic)
