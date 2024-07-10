"""Tests the CRUD actions in the CLI for taskforce"""

import unittest

from typer.testing import CliRunner

from justbuild import lfg_cli


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_info(self):
        result = self.runner.invoke(lfg_cli.app)
        self.assertEqual(result.exit_code, 0)
        self.assertGreater(len(result.stdout), 0)
        self.assertIn("version", result.stdout.lower().strip(), "version not in output")

    def test_help(self):
        result = self.runner.invoke(lfg_cli.app, ["--help"])
        self.assertEqual(result.exit_code, 0)


if __name__ == "__main__":
    unittest.main()
