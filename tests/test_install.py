import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class Installer(unittest.TestCase):
    def test_installs_selected_author_without_changing_existing_workflow(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            existing = target / '.github/workflows/existing.yml'
            existing.parent.mkdir(parents=True)
            existing.write_text('name: Existing\n')
            count = installer.install(target, 'example-user', 12345)
            self.assertGreater(count, 5)
            settings = json.loads((target / '.github/shizhen-fix/config.json').read_text())
            self.assertEqual(settings['author_id'], 12345)
            self.assertEqual(settings['author_login'], 'example-user')
            self.assertEqual(existing.read_text(), 'name: Existing\n')

    def test_conflicts_abort_before_copying_any_files(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            conflict = target / '.github/workflows/shizhen-review.yml'
            conflict.parent.mkdir(parents=True)
            conflict.write_text('keep this')
            with self.assertRaises(FileExistsError): installer.install(target, 'example', 1)
            self.assertEqual(conflict.read_text(), 'keep this')
            self.assertFalse((target / '.github/shizhen-fix/config.json').exists())

    def test_invalid_author_rejected_before_copying(self):
        with tempfile.TemporaryDirectory() as folder:
            for login, identity in [('bad/name', 1), ('valid', 0), ('valid', True)]:
                with self.assertRaises(ValueError): installer.install(Path(folder), login, identity)
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
