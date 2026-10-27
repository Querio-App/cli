#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'querio install: %s\n' "$*" >&2
  exit 1
}

if [[ ${1:-} == --help || ${1:-} == -h ]]; then
  printf 'Usage: bash install.sh [VERSION]\nDefault: 0.0.1\nDestination: QUERIO_INSTALL_DIR or ~/.local/bin\nRequires: curl and sha256sum or shasum\n'
  exit 0
fi
[[ $# -le 1 ]] || fail 'Expected one version argument; use --help.'
version=${1:-0.0.1}
version=${version#v}
[[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail 'Version must look like 0.0.1.'
command -v curl >/dev/null || fail 'Install curl to download Querio.'

case $(uname -s) in
  Darwin) os=darwin ;;
  Linux) os=linux ;;
  *) fail 'Supported systems: macOS and Linux.' ;;
esac
case $(uname -m) in
  x86_64|amd64) arch=amd64 ;;
  arm64|aarch64) arch=arm64 ;;
  *) fail 'Supported architectures: x86_64 and arm64.' ;;
esac

if command -v sha256sum >/dev/null; then
  hash=(sha256sum)
elif command -v shasum >/dev/null; then
  hash=(shasum -a 256)
else
  fail 'Install sha256sum or shasum to verify the download.'
fi

asset="querio_${version}_${os}_${arch}"
work=$(mktemp -d)
pending=
cleanup() {
  rm -rf "$work"
  if [[ -n $pending ]]; then rm -f "$pending"; fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'Downloading Querio %s (%s/%s)...\n' "$version" "$os" "$arch" >&2
release="https://github.com/Querio-App/cli/releases/download/v$version"
for file in "$asset" SHA256SUMS; do
  curl -fsSL "$release/$file" -o "$work/$file" || \
    fail 'Download failed. Check the version and your network connection.'
done
expected=$(awk -v name="$asset" '$2 == name { print $1 }' "$work/SHA256SUMS")
[[ $expected =~ ^[0-9a-f]{64}$ ]] || fail 'Checksum entry is missing or invalid.'
actual=$("${hash[@]}" "$work/$asset")
actual=${actual%% *}
[[ $actual == "$expected" ]] || fail 'Checksum mismatch; nothing was installed.'

install_dir=${QUERIO_INSTALL_DIR:-"$HOME/.local/bin"}
mkdir -p "$install_dir"
install_dir=$(cd "$install_dir" && pwd)
destination="$install_dir/querio"
[[ ! -L $destination ]] || fail 'Destination is a symlink; remove it explicitly before installing.'
[[ ! -e $destination || -f $destination ]] || fail 'Destination is not a regular file.'
pending=$(mktemp "$install_dir/.querio.XXXXXX")
cp "$work/$asset" "$pending"
chmod 755 "$pending"
installed_version=$("$pending" --version) || fail 'Downloaded binary could not run; existing installation was preserved.'
[[ $installed_version == "$version" ]] || fail 'Binary version mismatch; existing installation was preserved.'
mv -f "$pending" "$destination"
pending=
printf 'Installed Querio %s to %s\n' "$version" "$destination"
case ":${PATH:-}:" in
  *":$install_dir:"*) printf 'Run: querio --help\n' ;;
  *) printf 'Add %s to PATH, then run: querio --help\n' "$install_dir" ;;
esac
