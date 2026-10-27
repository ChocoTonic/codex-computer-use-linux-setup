import importlib.util
import json
from pathlib import Path, PurePosixPath
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('cu_setup', Path(__file__).resolve().parents[1]/'scripts/setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class ConfigTests(unittest.TestCase):
    def test_preserves_unrelated_settings(self):
        original = '# user preferences\nmodel = "example"\n[mcp_servers.other]\ncommand="other"\n'
        result = setup.config_with_entry(original, Path('/home/example/.local/bin/computer-use-linux'))
        self.assertTrue(result.startswith(original))
        self.assertNotIn('approval_policy', result)
        self.assertNotIn('sandbox_mode', result)

    def test_existing_entry_requires_explicit_replacement(self):
        original = '[mcp_servers.computer-use]\ncommand="old"\nargs=[]\n[mcp_servers.other]\ncommand="keep"\n'
        with self.assertRaises(ValueError):
            setup.config_with_entry(original, Path('/new'))
        updated = setup.config_with_entry(original, Path('/new'), True)
        self.assertIn('[mcp_servers.other]\ncommand="keep"', updated)
        self.assertNotIn('command="old"', updated)

    def test_repeated_install_retains_custom_options(self):
        text = '[mcp_servers.computer-use]\ncommand = "/new"\nargs = ["mcp"]\nstartup_timeout_sec=30\n'
        self.assertEqual(text, setup.config_with_entry(text, PurePosixPath('/new')))

    def test_invalid_toml_is_refused(self):
        with self.assertRaises(ValueError):
            setup.config_with_entry('model = [', Path('/new'))

    def test_table_text_inside_multiline_string_is_not_rewritten(self):
        text = 'instructions = """\n[mcp_servers.computer-use]\ncommand="old"\n"""\n'
        with self.assertRaises(ValueError):
            setup.config_with_entry(text, Path('/new'), True)

    def test_inline_and_noncanonical_config_is_refused(self):
        for text in ['mcp_servers = {}\n', 'mcp_servers.computer-use.command="old"\n', '[ mcp_servers.computer-use ]\ncommand="old"\n']:
            with self.assertRaises(ValueError):
                setup.config_with_entry(text, Path('/new'))


class RollbackTests(unittest.TestCase):
    def test_restore_existing_and_remove_new_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); old = root/'config'; new = root/'binary'; state = root/'audit'
            old.write_bytes(b'original')
            setup.install_files([(old, b'updated', 0o600), (new, b'new', 0o755)], state)
            setup.rollback(state/'manifest.json')
            self.assertEqual(old.read_bytes(), b'original')
            self.assertFalse(new.exists())

    def test_changed_file_blocks_all_rollback_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); a = root/'a'; b = root/'b'; state = root/'audit'
            a.write_bytes(b'old')
            setup.install_files([(a, b'installed', 0o600), (b, b'new', 0o600)], state)
            b.write_bytes(b'user edit')
            with self.assertRaises(ValueError):
                setup.rollback(state/'manifest.json')
            self.assertEqual(a.read_bytes(), b'installed')
            self.assertEqual(b.read_bytes(), b'user edit')

    def test_unchanged_files_are_not_owned_by_new_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); a=root/'a'; state=root/'audit'; a.write_bytes(b'same')
            self.assertEqual(0, setup.install_files([(a,b'same',0o600)],state))
            setup.rollback(state/'manifest.json')
            self.assertEqual(a.read_bytes(),b'same')


if __name__ == '__main__':
    unittest.main()
