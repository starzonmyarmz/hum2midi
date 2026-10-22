#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: scripts/release.sh <patch|minor|major|X.Y.Z>" >&2
  exit 1
}

[ $# -eq 1 ] || usage

repo="$(cd "$(dirname "$0")/.." && pwd)"
tap="${TAP_DIR:-$HOME/Code/homebrew-tap}"
formula="$tap/Formula/hum2midi.rb"

[ -f "$formula" ] || { echo "formula not found: $formula (set TAP_DIR)" >&2; exit 1; }
command -v gh >/dev/null || { echo "gh is required" >&2; exit 1; }

cd "$repo"
[ "$(git branch --show-current)" = main ] || { echo "must be on main" >&2; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "working tree is dirty" >&2; exit 1; }
[ -z "$(git -C "$tap" status --porcelain)" ] || { echo "tap working tree is dirty" >&2; exit 1; }
git pull --ff-only
git -C "$tap" pull --ff-only

current="$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)"
IFS=. read -r major minor patch <<<"$current"

case "$1" in
  patch) new="$major.$minor.$((patch + 1))" ;;
  minor) new="$major.$((minor + 1)).0" ;;
  major) new="$((major + 1)).0.0" ;;
  [0-9]*.[0-9]*.[0-9]*) new="$1" ;;
  *) usage ;;
esac

tag="v$new"
git rev-parse -q --verify "refs/tags/$tag" >/dev/null && { echo "tag $tag already exists" >&2; exit 1; }

echo "Releasing $current -> $new"
read -r -p "Continue? [y/N] " answer
[ "$answer" = y ] || exit 1

perl -pi -e "s/^version = \".*\"/version = \"$new\"/" pyproject.toml
git commit -am "chore: bump version to $new"
git tag "$tag"
git push origin main --tags
gh release create "$tag" --title "$tag" --generate-notes

perl -pi -e "s/tag: \"v[^\"]*\"/tag: \"$tag\"/" "$formula"
git -C "$tap" commit -am "chore: bump hum2midi to $tag"
git -C "$tap" push origin main

echo "Released $tag"
