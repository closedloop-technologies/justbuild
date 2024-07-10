import json
import os
import random
import string
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from justbuild.helpers import snakecase
from justbuild.initialize import get_justbuild_config, initialize
from justbuild.models import justbuildInfo


class TestInitialize(unittest.TestCase):
    @patch(
        "typer.prompt",
        side_effect=[
            "My Package",
            "https://github.com/user/template_package",
            "A short description",
            "localhost",
            "0.2.0",
        ],
    )
    @patch("typer.confirm", side_effect=["y"])
    def test_cli_inputs(self, *_mocks):
        curdir = Path(os.getcwd())
        temp_dir = tempfile.TemporaryDirectory(prefix="justbuild", suffix="test")
        temp_dir_path = Path(temp_dir.name)
        temp_dir_path.mkdir(parents=True, exist_ok=True)
        os.chdir(temp_dir_path.resolve())
        qr_info = get_justbuild_config(
            None, None, None, None, None, config_dir=temp_dir_path
        )
        self.assertEqual(qr_info.name, "My Package")
        self.assertEqual(qr_info.description, "A short description")
        self.assertEqual(qr_info.version, "0.2.0")
        self.assertEqual(qr_info.repo, "localhost")
        self.assertEqual(qr_info.template, "https://github.com/user/template_package")

        # test if .justbuild is created
        self.assertTrue((temp_dir_path / ".justbuild").exists())

        with open(temp_dir_path / ".justbuild") as f:
            config = justbuildInfo(**json.load(f))
        self.assertEqual(config, qr_info)

        os.chdir(curdir)
        temp_dir.cleanup()

    def test_initialize(self):
        curdir = Path(os.getcwd())
        temp_dir = tempfile.TemporaryDirectory(prefix="justbuild", suffix="test")
        # change working directory to temp_dir
        os.chdir(temp_dir.name)

        random_suffix = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=5)
        )
        qr_info, template_dir = initialize(
            f"example-package-{random_suffix}",
            "https://github.com/closedloop-technologies/justbuild-base",
            "Example package description",
            "http://localhost/repo",
            "0.9.9",
            force=False,
        )

        self.assertEqual(qr_info.name, f"example-package-{random_suffix}")
        self.assertEqual(qr_info.description, "Example package description")
        self.assertEqual(
            qr_info.template,
            "https://github.com/closedloop-technologies/justbuild-base",
        )
        self.assertEqual(qr_info.version, "0.9.9")
        self.assertIn(f"/example-package-{random_suffix}", qr_info.repo)

        os.chdir(template_dir.name)
        git_file_status = subprocess.check_output(["git", "status", "--short"])
        changes = sorted(
            [l.strip().split() for l in git_file_status.decode("utf-8").splitlines()]
        )
        package_name = (snakecase(qr_info.name) or "").replace("-", "_")
        self.assertListEqual(
            changes,
            [
                ["??", f"{package_name}/"],
                ["D", "justbuild_base/__init__.py"],
                ["D", "justbuild_base/__main__.py"],
                ["D", "justbuild_base/cli.py"],
                ["D", "justbuild_base/config.py"],
                ["M", ".coveragerc"],
                ["M", "Dockerfile"],
                ["M", "README.md"],
                ["M", "pyproject.toml"],
                ["M", "tests/test_cli.py"],
                ["M", "tests/test_config.py"],
                ["M", "tests/test_install.py"],
            ],
        )

        # Check that github repo was created and configured properly
        repo_info = subprocess.check_output(["gh", "repo", "view", qr_info.repo])
        self.assertEqual(
            repo_info.splitlines()[0].decode("utf-8"),
            f"name:\t{qr_info.repo.split('github.com/')[-1]}",
        )
        self.assertEqual(
            repo_info.splitlines()[1].decode("utf-8").strip(),
            "description:\tExample package description",
        )

        # Delete the repo
        try:
            repo_info = os.system(f"gh repo delete {qr_info.repo} --yes")
        except Exception as e:
            print(f"Need to delete repo manually: {qr_info.repo}\n{e}")

        # Delete the temp_dir
        temp_dir.cleanup()
        os.chdir(curdir)

    def test_update_existing_with_template(self):
        """Create a new github repo and then run update cli"""

        curdir = Path(os.getcwd())
        temp_dir = tempfile.TemporaryDirectory(prefix="justbuild", suffix="test")
        # change working directory to temp_dir
        os.chdir(temp_dir.name)
        random_suffix = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=5)
        )
        name = f"example-toupdate-{random_suffix}"
        os.system("touch random-empty-file.txt")
        os.system("git init")
        print(temp_dir.name)

        qr_info, template_dir = initialize(
            name,
            "https://github.com/closedloop-technologies/justbuild-base",
            "Example package description",
            "http://localhost/repo",
            "0.9.9",
            force=True,
        )

        self.assertEqual(str(template_dir.resolve()), temp_dir.name)

        self.assertEqual(qr_info.name, f"example-toupdate-{random_suffix}")
        self.assertEqual(qr_info.description, "Example package description")
        self.assertEqual(
            qr_info.template,
            "https://github.com/closedloop-technologies/justbuild-base",
        )
        self.assertEqual(qr_info.version, "0.9.9")
        self.assertEqual("http://localhost/repo", qr_info.repo)

        os.chdir(template_dir)
        git_file_status = subprocess.check_output(["git", "status", "--short"])
        changes = sorted(
            [l.strip().split() for l in git_file_status.decode("utf-8").splitlines()]
        )
        package_name = (snakecase(qr_info.name) or "").replace("-", "_")
        self.assertListEqual(
            changes,
            [
                ["??", ".justbuild"],
                ["??", f"{package_name}/"],
                ["??", "random-empty-file.txt"],
                ["D", "justbuild_base/__init__.py"],
                ["D", "justbuild_base/__main__.py"],
                ["D", "justbuild_base/cli.py"],
                ["D", "justbuild_base/config.py"],
                ["M", ".coveragerc"],
                ["M", "Dockerfile"],
                ["M", "README.md"],
                ["M", "pyproject.toml"],
                ["M", "tests/test_cli.py"],
                ["M", "tests/test_config.py"],
                ["M", "tests/test_install.py"],
            ],
        )

        temp_dir.cleanup()
        os.chdir(curdir)


if __name__ == "__main__":
    # unittest.main()
    t = TestInitialize()
    t.test_update_existing_with_template()
