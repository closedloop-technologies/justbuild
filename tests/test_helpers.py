import unittest

from justbuild.helpers import snakecase


class TestHelpers(unittest.TestCase):
    def test_snakecase(self):
        self.assertEqual(snakecase("Hello World"), "hello_world")
        self.assertEqual(snakecase("HelloWorld "), "hello_world")
        self.assertEqual(snakecase("helloWorld"), "hello_world")
        self.assertEqual(snakecase(" hello_world"), "hello_world")
        self.assertEqual(snakecase("hello123World"), "hello123_world")
        self.assertEqual(snakecase("123helloWorld"), "123_hello_world")
        self.assertEqual(snakecase("helloworld"), "helloworld")
        self.assertEqual(snakecase(""), "")
        self.assertEqual(snakecase(None), None)
        self.assertEqual(snakecase("X"), "x")
        self.assertEqual(snakecase("k9dog"), "k9_dog")


if __name__ == "__main__":
    unittest.main()
