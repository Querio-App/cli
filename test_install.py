import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


INSTALLER = Path(__file__).with_name("install.sh")


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.assets = self.root / "assets"
        self.assets.mkdir()
        self.destination = self.root / "install with spaces" / "querio"
        self.destination.parent.mkdir()
        self.destination.write_text("existing installation")
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "HOME": str(self.root),
            "QUERIO_INSTALL_DIR": str(self.destination.parent),
            "TEST_ROOT": str(self.root),
            "TEST_OS": "Linux",
            "TEST_ARCH": "x86_64",
            "TEST_FAIL_DOWNLOAD": "",
        }
        self.executable("uname", '#!/bin/sh\ncase "$1" in -s) echo "$TEST_OS";; -m) echo "$TEST_ARCH";; esac\n')
        self.executable("curl", f"#!{sys.executable}\n" + '''import json, os, pathlib, shutil, sys
args = sys.argv[1:]
assert len(args) == 4 and args[0] == "-fsSL" and args[2] == "-o"
prefix = "https://github.com/Querio-App/cli/releases/download/v0.0.1/"
assert args[1].startswith(prefix)
name = args[1][len(prefix):]
root = pathlib.Path(os.environ["TEST_ROOT"])
requested = root / "requested.json"
names = json.loads(requested.read_text()) if requested.exists() else []
requested.write_text(json.dumps(names + [name]))
destination = pathlib.Path(args[3])
(root / "download-dir").write_text(str(destination.parent))
if os.environ["TEST_FAIL_DOWNLOAD"] in ("1", name):
    sys.exit(1)
shutil.copyfile(root / "assets" / name, destination)
''')
        self.fixture()

    def executable(self, name, content):
        path = self.bin / name
        path.write_text(content)
        path.chmod(0o755)

    def fixture(self, os_name="linux", arch="amd64", version="0.0.1"):
        name = f"querio_0.0.1_{os_name}_{arch}"
        content = f"#!/bin/sh\nprintf '{version}\\n'\n".encode()
        (self.assets / name).write_bytes(content)
        (self.assets / "SHA256SUMS").write_text(f"{hashlib.sha256(content).hexdigest()}  {name}\n")
        return name

    def run_installer(self, *args):
        (self.root / "requested.json").unlink(missing_ok=True)
        result = subprocess.run(["bash", str(INSTALLER), *args], env=self.env, capture_output=True, text=True)
        downloaded = self.root / "download-dir"
        if downloaded.exists():
            self.assertFalse(Path(downloaded.read_text()).exists())
        self.assertEqual(list(self.destination.parent.glob(".querio.*")), [])
        return result

    def assert_preserved(self, result, message):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)
        self.assertEqual(self.destination.read_text(), "existing installation")

    def test_platforms_install_and_replace(self):
        for system, machine, os_name, arch in [
            ("Linux", "x86_64", "linux", "amd64"),
            ("Linux", "aarch64", "linux", "arm64"),
            ("Darwin", "x86_64", "darwin", "amd64"),
            ("Darwin", "arm64", "darwin", "arm64"),
        ]:
            with self.subTest(system=system, machine=machine):
                name = self.fixture(os_name, arch)
                self.env.update(TEST_OS=system, TEST_ARCH=machine)
                result = self.run_installer("v0.0.1")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads((self.root / "requested.json").read_text()), [name, "SHA256SUMS"])
                self.assertEqual(self.destination.stat().st_mode & 0o777, 0o755)
                self.assertEqual(subprocess.check_output([self.destination, "--version"], text=True), "0.0.1\n")

    def test_bad_checksum_preserves_installation(self):
        (self.assets / "querio_0.0.1_linux_amd64").write_text("corrupted download")
        self.assert_preserved(self.run_installer(), "Checksum mismatch")

    def test_missing_or_duplicate_checksum_preserves_installation(self):
        sums = self.assets / "SHA256SUMS"
        original = sums.read_text()
        for content in ["", original + original]:
            with self.subTest(content=content):
                sums.write_text(content)
                self.assert_preserved(self.run_installer(), "Checksum entry is missing or invalid")

    def test_download_failure_preserves_installation(self):
        for name in ["querio_0.0.1_linux_amd64", "SHA256SUMS"]:
            with self.subTest(asset=name):
                self.env["TEST_FAIL_DOWNLOAD"] = name
                self.assert_preserved(self.run_installer(), "Download failed")

    def test_wrong_binary_version_preserves_installation(self):
        self.fixture(version="0.0.2")
        self.assert_preserved(self.run_installer(), "Binary version mismatch")

    def test_symlink_is_not_replaced(self):
        target = self.root / "target"
        self.destination.rename(target)
        self.destination.symlink_to(target)
        self.assert_preserved(self.run_installer(), "Destination is a symlink")
        self.assertTrue(self.destination.is_symlink())

    def test_unsupported_platform_does_not_download(self):
        self.env["TEST_OS"] = "FreeBSD"
        self.assert_preserved(self.run_installer(), "Supported systems")
        self.assertFalse((self.root / "requested.json").exists())

    def test_help_and_invalid_version_do_not_download(self):
        result = self.run_installer("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stdout)
        self.assert_preserved(self.run_installer("../0.0.1"), "Version must look like")
        self.assertFalse((self.root / "requested.json").exists())

    def test_default_install_directory(self):
        del self.env["QUERIO_INSTALL_DIR"]
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / ".local/bin/querio").is_file())

    @unittest.skipUnless(shutil.which("shasum"), "shasum not installed")
    def test_shasum_fallback(self):
        for name in ["bash", "shasum", "awk", "mktemp", "rm", "mkdir", "cp", "chmod", "mv"]:
            (self.bin / name).symlink_to(shutil.which(name))
        self.env["PATH"] = str(self.bin)
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
