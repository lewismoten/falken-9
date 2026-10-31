#!/bin/sh
# Install a pinned assembler into ignored project build storage; no sudo.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
target="$root/build/tools/64tass"
assembler="$target/usr/bin/64tass"
if [ ! -x "$assembler" ]; then
  if command -v apt >/dev/null 2>&1 && command -v dpkg-deb >/dev/null 2>&1; then
    mkdir -p "$target"
    (
      cd "$target"
      apt download 64tass=1.60.3243-1build1
      deb=$(printf '%s\n' 64tass_*.deb)
      dpkg-deb -x "$deb" .
      rm "$deb"
    )
  else
    printf '%s\n' 'Automatic bootstrap requires apt/dpkg-deb.' >&2
    printf '%s\n' 'Otherwise install 64tass 1.60.3243 and set TASS64 to its executable.' >&2
    exit 1
  fi
fi
version=$("$assembler" --version)
case "$version" in
  *V1.60.3243*) printf '%s\n' "$version" ;;
  *) printf '%s\n' "Unexpected assembler version: $version" >&2; exit 1 ;;
esac
