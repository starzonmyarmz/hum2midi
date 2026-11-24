#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: scripts/release.sh <patch|minor|major|X.Y.Z>" >&2
  exit 1
}

[ $# -eq 1 ] || usage

repo="$(cd "$(dirname "$0")/.." && pwd)"

command -v gh >/dev/null || { echo "gh is required" >&2; exit 1; }

cd "$repo"
[ "$(git branch --show-current)" = main ] || { echo "must be on main" >&2; exit 1; }
[ -z "$(git status --porcelain)" ] || { echo "working tree is dirty" >&2; exit 1; }
git pull --ff-only

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

gh workflow enable update.yml -R starzonmyarmz/homebrew-tap
gh workflow run update.yml -R starzonmyarmz/homebrew-tap

echo "Released $tag. The tap's Update workflow is rendering the formula."
