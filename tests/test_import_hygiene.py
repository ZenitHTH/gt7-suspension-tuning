#!/usr/bin/env python3
"""Import-hygiene regression guard.

Python 3.14+ (PEP 649) evaluates annotations lazily, so a name used in a
signature but never imported (e.g. `Optional` without a typing import)
passes silently on 3.14+ while crashing on 3.12 — which is what CI runs.
This test statically fails on any module that uses a typing name in
annotations without importing it.
"""
import ast
import os
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TYPING_NAMES = {'Optional', 'List', 'Dict', 'Tuple', 'Set', 'FrozenSet', 'Type', 'Union'}


class TestImportHygiene(unittest.TestCase):
    def _typing_names(self, tree):
        imported, used = set(), set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split('.')[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.module.split('.')[0] == 'typing':
                imported.update(a.name for a in node.names)
            if isinstance(node, ast.Name) and node.id in TYPING_NAMES:
                used.add(node.id)
            elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                    and node.value.id == 'typing':
                used.add(node.attr)
        return imported, used

    def test_no_module_uses_typing_names_without_import(self):
        offenders = []
        for root, dirs, files in os.walk(BASE_DIR):
            dirs[:] = [d for d in dirs if d not in ('.venv', '__pycache__', 'dist', 'build', '.git')]
            for name in files:
                if not name.endswith('.py'):
                    continue
                path = os.path.join(root, name)
                with open(path, encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=path)
                imported, used = self._typing_names(tree)
                missing = used - imported
                if missing:
                    offenders.append(f'{os.path.relpath(path, BASE_DIR)}: {sorted(missing)}')
        self.assertEqual(offenders, [], 'typing names used without import (crashes on py3.12): '
                                         + '; '.join(offenders))


if __name__ == '__main__':
    unittest.main()