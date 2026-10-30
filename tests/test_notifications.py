"""Offline notification-wrapper checks. No real notify process or network is used."""

import os
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRAPPERS = ("dalfox-notify.sh", "sqlmap-notify.sh")
BASH = os.environ.get("XHUNT_TEST_BASH") or shutil.which("bash")


@unittest.skipUnless(BASH, "Bash is required; set XHUNT_TEST_BASH if needed")
class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="xhunt-notify-test-")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.bin = self.work / "bin"
        self.bin.mkdir()
        self.args_file = self.work / "args"
        self.stdin_file = self.work / "stdin"
        fake = self.bin / "notify"
        fake.write_text(
            "#!/bin/bash\n"
            "printf '%s\\0' \"$@\" > \"$MOCK_CAPTURE_ARGS\"\n"
            "cat > \"$MOCK_CAPTURE_STDIN\"\n"
            "exit \"$MOCK_EXIT_CODE\"\n",
            encoding="utf-8",
            newline="\n",
        )
        fake.chmod(0o755)
        self.config = self.work / "provider config.local.yaml"
        self.config.write_text("discord: []\n", encoding="utf-8")
        self.env = os.environ.copy()
        self.env.pop("NOTIFY_PROVIDER_CONFIG", None)
        self.env["PATH"] = str(self.bin) + os.pathsep + self.env.get("PATH", "")
        self.env["MOCK_CAPTURE_ARGS"] = self.args_file.as_posix()
        self.env["MOCK_CAPTURE_STDIN"] = self.stdin_file.as_posix()
        self.env["MOCK_EXIT_CODE"] = "0"

    def run_wrapper(self, name, *args, config=None, exit_code=0):
        env = self.env.copy()
        if config is not None:
            env["NOTIFY_PROVIDER_CONFIG"] = config
        env["MOCK_EXIT_CODE"] = str(exit_code)
        # Send a quoted command on stdin so Windows/MSYS startup cannot expand
        # wildcard arguments before the wrapper receives them.
        command = 'exec "$BASH" ' + shlex.join(
            [(ROOT / "notify" / name).as_posix(), *args]
        ) + "\n"
        return subprocess.run(
            [BASH, "-s"], input=command.encode(),
            env=env, capture_output=True, check=False, cwd=ROOT,
        )

    def clear_capture(self):
        self.args_file.unlink(missing_ok=True)
        self.stdin_file.unlink(missing_ok=True)

    def test_unset_configuration_never_invokes_notify(self):
        for name in WRAPPERS:
            with self.subTest(wrapper=name):
                result = self.run_wrapper(name, "ignored")
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")
                self.assertEqual(result.stderr, b"")
                self.assertFalse(self.args_file.exists())
                self.assertFalse(self.stdin_file.exists())

    def test_empty_configuration_never_invokes_notify(self):
        for name in WRAPPERS:
            with self.subTest(wrapper=name):
                result = self.run_wrapper(name, "ignored", config="")
                self.assertEqual(result.returncode, 0)
                self.assertFalse(self.args_file.exists())

    def test_missing_configuration_fails_before_notify(self):
        missing = (self.work / "missing.yaml").as_posix()
        for name in WRAPPERS:
            with self.subTest(wrapper=name):
                result = self.run_wrapper(name, "ignored", config=missing)
                self.assertEqual(result.returncode, 2)
                self.assertIn(b"readable regular file", result.stderr)
                self.assertNotIn(missing.encode(), result.stderr)
                self.assertFalse(self.args_file.exists())

    def test_directory_configuration_fails_before_notify(self):
        for name in WRAPPERS:
            with self.subTest(wrapper=name):
                result = self.run_wrapper(name, "ignored", config=self.work.as_posix())
                self.assertEqual(result.returncode, 2)
                self.assertFalse(self.args_file.exists())

    @unittest.skipIf(
        os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
        "Unreadable permission bits require a non-root POSIX user",
    )
    def test_unreadable_configuration_fails_before_notify(self):
        self.config.chmod(0)
        self.addCleanup(self.config.chmod, 0o600)
        for name in WRAPPERS:
            with self.subTest(wrapper=name):
                result = self.run_wrapper(name, "ignored", config=self.config.as_posix())
                self.assertEqual(result.returncode, 2)
                self.assertFalse(self.args_file.exists())

    def test_explicit_path_and_literal_arguments_reach_mock(self):
        arguments = ("-n", r"back\slash", "*", "$(touch SHOULD_NOT_EXIST)", "two words")
        for name in WRAPPERS:
            with self.subTest(wrapper=name):
                self.clear_capture()
                result = self.run_wrapper(name, *arguments, config=self.config.as_posix())
                self.assertEqual(result.returncode, 0, result.stderr)
                actual = self.args_file.read_bytes().split(b"\0")[:-1]
                self.assertEqual(
                    actual,
                    [
                        b"-silent", b"-disable-update-check", b"-id", b"dalfox",
                        b"-provider-config", self.config.as_posix().encode(),
                    ],
                )
                self.assertEqual(
                    self.stdin_file.read_bytes(),
                    (" ".join(arguments) + "\n").encode(),
                )
                self.assertEqual(result.stdout, b"")
                self.assertFalse((ROOT / "SHOULD_NOT_EXIST").exists())

    def test_notify_failure_exit_status_propagates(self):
        for name in WRAPPERS:
            with self.subTest(wrapper=name):
                self.clear_capture()
                result = self.run_wrapper(
                    name, "inert input", config=self.config.as_posix(), exit_code=23,
                )
                self.assertEqual(result.returncode, 23)
                self.assertTrue(self.args_file.exists())


class BuildContextTests(unittest.TestCase):
    def test_tracked_provider_configuration_is_retired(self):
        lines = (ROOT / "notify" / "provider-config.yaml").read_text().splitlines()
        active = [line for line in lines if line.strip() and not line.startswith("#")]
        self.assertEqual(active, ["discord: []"])

    def test_dockerfile_copies_only_notification_scripts(self):
        text = (ROOT / "Dockerfile").read_text()
        copy_lines = [
            line for line in text.splitlines()
            if line.startswith(("ADD ", "COPY ")) and "notify" in line
        ]
        self.assertEqual(
            copy_lines,
            ["COPY ./notify/dalfox-notify.sh ./notify/sqlmap-notify.sh ./notify/"],
        )

    def test_build_context_and_git_ignore_local_secrets(self):
        docker = (ROOT / ".dockerignore").read_text().splitlines()
        ignored = (ROOT / ".gitignore").read_text().splitlines()
        for rule in (".git", ".env", ".env.*", "**/.env", "**/.env.*",
                     "**/provider-config*.yaml", "**/provider-config*.yml"):
            self.assertIn(rule, docker)
        for rule in (".env", ".env.*", "**/provider-config*.yaml",
                     "**/provider-config*.yml", "notify/local/"):
            self.assertIn(rule, ignored)
        self.assertIn("!notify/provider-config.yaml", ignored)


if __name__ == "__main__":
    unittest.main()
