import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from appimage_integrator import cli


class UtilityTests(unittest.TestCase):
    def test_slugify_spaces_and_punctuation(self):
        self.assertEqual(cli.slugify("My Great App!"), "my-great-app")

    def test_slugify_fallback(self):
        self.assertEqual(cli.slugify(" !!! "), "appimage-app")

    def test_desktop_escape_newline(self):
        self.assertEqual(cli.desktop_escape("A\nB"), "A\\nB")

    def test_exec_quote_spaces(self):
        self.assertEqual(cli.exec_quote(Path("/tmp/My App.AppImage")), '"/tmp/My App.AppImage"')


class InstallLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.app_root = self.base / "opt"
        self.desktop_root = self.base / "applications"
        self.icon_root = self.base / "icons"
        self.manifest_root = self.base / "manifests"
        self.source = self.base / "Original App.AppImage"
        self.source.write_bytes(b"not executed; test fixture")
        self.source.chmod(0o644)
        self.patches = [
            patch.object(cli, "APP_ROOT", self.app_root),
            patch.object(cli, "DESKTOP_ROOT", self.desktop_root),
            patch.object(cli, "ICON_ROOT", self.icon_root),
            patch.object(cli, "MANIFEST_ROOT", self.manifest_root),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, **overrides):
        values = dict(appimage=str(self.source), name="Test App", id="test-app",
                      icon=None, move=False, dry_run=False)
        values.update(overrides)
        return Namespace(**values)

    def test_install_copies_and_creates_desktop_and_manifest(self):
        self.assertEqual(cli.install(self.args()), 0)
        installed = self.app_root / "test-app" / self.source.name
        self.assertTrue(self.source.exists(), "copy mode must preserve the original")
        self.assertTrue(installed.exists())
        self.assertTrue(installed.stat().st_mode & 0o111)
        desktop = self.desktop_root / "test-app.desktop"
        self.assertIn("Name=Test App", desktop.read_text())
        self.assertIn('Exec="', desktop.read_text())
        manifest = json.loads((self.manifest_root / "test-app.json").read_text())
        self.assertEqual(manifest["id"], "test-app")

    def test_move_mode_moves_source_into_managed_directory(self):
        self.assertEqual(cli.install(self.args(move=True)), 0)
        installed = self.app_root / "test-app" / self.source.name
        self.assertFalse(self.source.exists())
        self.assertTrue(installed.exists())

    def test_dry_run_does_not_write(self):
        self.assertEqual(cli.install(self.args(dry_run=True)), 0)
        self.assertTrue(self.source.exists())
        self.assertFalse(self.app_root.exists())
        self.assertFalse(self.desktop_root.exists())

    def test_duplicate_install_refused(self):
        self.assertEqual(cli.install(self.args()), 0)
        with self.assertRaises(cli.IntegrationError):
            cli.install(self.args())

    def test_uninstall_keeps_appimage_by_default(self):
        self.assertEqual(cli.install(self.args()), 0)
        self.assertEqual(cli.uninstall(Namespace(id="test-app", dry_run=False, remove_appimage=False)), 0)
        self.assertTrue((self.app_root / "test-app" / self.source.name).exists())
        self.assertFalse((self.desktop_root / "test-app.desktop").exists())
        self.assertFalse((self.manifest_root / "test-app.json").exists())

    def test_failed_manifest_write_restores_moved_source(self):
        with patch.object(cli, "save_json_atomic", side_effect=OSError("simulated disk error")):
            with self.assertRaises(OSError):
                cli.install(self.args(move=True))
        self.assertTrue(self.source.exists())
        self.assertFalse((self.app_root / "test-app" / self.source.name).exists())
        self.assertFalse((self.desktop_root / "test-app.desktop").exists())

    def test_failed_manifest_write_rolls_back_copy_and_desktop(self):
        with patch.object(cli, "save_json_atomic", side_effect=OSError("simulated disk error")):
            with self.assertRaises(OSError):
                cli.install(self.args())
        self.assertTrue(self.source.exists())
        self.assertFalse((self.app_root / "test-app" / self.source.name).exists())
        self.assertFalse((self.desktop_root / "test-app.desktop").exists())

    def test_uninstall_rejects_manifest_path_escape(self):
        cli.install(self.args())
        manifest_path = self.manifest_root / "test-app.json"
        data = json.loads(manifest_path.read_text())
        data["desktop_file"] = str(self.base / "important-file")
        manifest_path.write_text(json.dumps(data))
        with self.assertRaises(cli.IntegrationError):
            cli.uninstall(Namespace(id="test-app", dry_run=False, remove_appimage=True))


if __name__ == "__main__":
    unittest.main()
