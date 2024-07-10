import unittest
from subprocess import run


class TestInstall(unittest.TestCase):
    def test_library_installed(self):
        import justbuild

        self.assertIsNotNone(justbuild)

    def test_module(self):
        run(["python", "-m", "justbuild", "--help"])

    def test_consolescript(self):
        run(["lfg", "--help"])
