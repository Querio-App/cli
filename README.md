# Querio CLI

Querio from your terminal or coding agent. Private distribution for macOS and Linux, on Intel/AMD and ARM64.

## Install 0.0.1

Requires [GitHub CLI](https://cli.github.com/) and access to this repository.

```sh
gh auth login
tmp=$(mktemp -d)
gh release download v0.0.1 -R Querio-App/cli -p install.sh -D "$tmp" &&
  bash "$tmp/install.sh" 0.0.1
rm -rf "$tmp"
```

The installer verifies SHA-256 checksums and installs to `~/.local/bin`. Add that directory to `PATH` if prompted. Set `QUERIO_INSTALL_DIR` to choose another location. Rerunning replaces an existing regular-file installation.

## Use

```sh
querio login
querio --help
querio code skill
```

Every command has `--help`. Downloads are private; API permissions still come from your Querio account. Do not redistribute.

Uninstall: `rm ~/.local/bin/querio` (or remove it from your chosen install directory). Credentials are left untouched.
