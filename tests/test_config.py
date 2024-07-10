import unittest

from justbuild.config import Config


class TestConfig(unittest.TestCase):
    def test_configclass(self):
        config = Config()
        self.assertIsInstance(config, Config, msg="config is not a Config")
        self.assertEqual(config.name, "justbuild", msg="config.name is not 'justbuild'")


if __name__ == "__main__":
    unittest.main()
