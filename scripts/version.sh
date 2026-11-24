read_version() {
  sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1
}

write_version() {
  sed -i '' "1,/^version = /s/^version = \".*\"/version = \"$1\"/" pyproject.toml
}
