class Hum2midi < Formula
  desc "Convert hummed or monophonic audio recordings to quantized MIDI"
  homepage "https://github.com/starzonmyarmz/hum2midi"
  url "https://github.com/starzonmyarmz/hum2midi.git", tag: "v@VERSION@", using: :git
  license "MIT"

  depends_on "python@3.12"
  depends_on "ffmpeg"

  def install
    system Formula["python@3.12"].opt_bin/"python3.12", "-m", "venv", libexec
    system libexec/"bin/pip", "install", "--no-cache-dir", buildpath
    bin.install_symlink libexec/"bin/hum2midi"
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/hum2midi --version")
  end
end
