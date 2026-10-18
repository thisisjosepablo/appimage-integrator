import unittest
from pathlib import Path
from appimage_integrator.cli import desktop_escape, exec_quote, slugify


class UtilityTests(unittest.TestCase):
    def test_slugify_spaces_and_punctuation(self):
        self.assertEqual(slugify("My Great App!"), "my-great-app")

    def test_slugify_fallback(self):
        self.assertEqual(slugify(" !!! "), "appimage-app")

    def test_desktop_escape_newline(self):
        self.assertEqual(desktop_escape("A\nB"), "A\\nB")

    def test_exec_quote_spaces(self):
        self.assertEqual(exec_quote(Path("/tmp/My App.AppImage")), '"/tmp/My App.AppImage"')


if __name__ == "__main__":
    unittest.main()
