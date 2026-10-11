"""Test terminal output and color policy."""

import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEMO = (
    "source scripts/ci/ui.sh; "
    "ci_ui_init; ci_ui_banner TEST; "
    "ci_ui_stage CHECKS; ci_ui_pass Example; "
    "ci_ui_finish Complete"
)


class OperatorUITests(unittest.TestCase):
    def output(self, color="auto", no_color=False):
        env = dict(os.environ)
        env["CI_COLOR"] = color
        env.pop("NO_COLOR", None)

        if no_color:
            env["NO_COLOR"] = "1"

        result = subprocess.run(
            ["bash", "-c", DEMO],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def test_plain_noninteractive(self):
        result = self.output()
        self.assertNotIn("\x1b[", result)
        self.assertIn("SUCCESS", result)

    def test_forced_color(self):
        self.assertIn("\x1b[", self.output("always"))

    def test_no_color_override(self):
        self.assertNotIn(
            "\x1b[", self.output("always", no_color=True)
        )

    def test_explicit_plain_output(self):
        self.assertNotIn("\x1b[", self.output("never"))


if __name__ == "__main__":
    unittest.main()
