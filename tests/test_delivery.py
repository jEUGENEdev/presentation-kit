import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import build
from scripts.package_delivery import package


class DeliveryTests(unittest.TestCase):
    def test_copy_is_identifiable_and_preserves_exact_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = build.build(folder / 'source.html')
            target = package(folder / 'delivery', source=source)
            self.assertEqual(source.read_bytes(), target.read_bytes())
            manifest = json.loads((target.parent / 'manifest.json').read_text())
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(manifest['sha256'], digest)
            self.assertEqual(manifest['file'], target.name)
            self.assertEqual(manifest['size_bytes'], source.stat().st_size)
            self.assertIn(digest[:12], target.name)
            self.assertEqual(package(target.parent, source=source), target)

    def test_stale_html_is_rejected_before_creating_delivery(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            source = build.build(folder / 'source.html')
            source.write_bytes(source.read_bytes() + b'<!-- stale edit -->')
            with self.assertRaisesRegex(ValueError, 'differs from current sources'):
                package(folder / 'delivery', source=source)
            self.assertFalse((folder / 'delivery').exists())
