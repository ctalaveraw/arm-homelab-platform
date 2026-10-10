"""Fail-closed fault-injection tests for the Prometheus storage guard."""

import runpy
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
GUARD = ROOT / "compose/observability/check-storage.py"


class PrometheusGuardFailureTests(unittest.TestCase):
    def exercise_guard(
        self,
        *,
        directory_access=0,
        mount_status=0,
        mount_label="storage_sdcard",
    ):
        """Intercept host commands so no real filesystem is altered."""
        commands = []

        def fake_run(argv, **kwargs):
            commands.append(list(argv))

            if argv[0] == "/usr/bin/ls":
                return subprocess.CompletedProcess(
                    argv,
                    directory_access,
                    stdout="",
                    stderr="",
                )

            if argv[0] == "/usr/bin/findmnt":
                return subprocess.CompletedProcess(
                    argv,
                    mount_status,
                    stdout=f"{mount_label}\n",
                    stderr="",
                )

            self.fail(f"Unexpected command: {argv}")

        with (
            patch("subprocess.run", side_effect=fake_run),
            self.assertRaises(SystemExit) as caught,
        ):
            runpy.run_path(str(GUARD), run_name="__main__")

        message = str(caught.exception)

        self.assertIn(
            "Prometheus storage preflight FAILED",
            message,
        )

        return message, commands

    def test_inaccessible_sd_directory_is_rejected(self):
        message, commands = self.exercise_guard(
            directory_access=1,
        )

        self.assertIn("Command failed: /usr/bin/ls", message)
        self.assertEqual(len(commands), 1)

    def test_missing_sd_mount_is_rejected(self):
        message, commands = self.exercise_guard(
            mount_status=1,
        )

        self.assertIn("Command failed: /usr/bin/findmnt", message)
        self.assertEqual(len(commands), 2)

    def test_wrong_sd_label_is_rejected(self):
        message, commands = self.exercise_guard(
            mount_label="unexpected_filesystem",
        )

        self.assertIn("Expected labeled ext4", message)
        self.assertEqual(len(commands), 2)


if __name__ == "__main__":
    unittest.main()
