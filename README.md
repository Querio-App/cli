# Querio CLI

Querio from your terminal or coding agent. Available for macOS and Linux, on Intel/AMD and ARM64.

## Install 0.0.1

Requires `curl` and either `sha256sum` or `shasum`. No GitHub account or authentication is needed.

```sh
tmp=$(mktemp -d)
curl -fsSL https://raw.githubusercontent.com/Querio-App/cli/main/install.sh -o "$tmp/install.sh" &&
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

Every command has `--help`. The CLI is publicly available; API permissions come from your Querio account.

Uninstall: `rm ~/.local/bin/querio` (or remove it from your chosen install directory). Credentials are left untouched.
