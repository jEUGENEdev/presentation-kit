"""Verify the committed HTML and create an identifiable copy for delivery."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build


def package(output_dir=None, source=None, root=ROOT):
    source = Path(source) if source else root / 'dist/index.html'
    payload = source.read_bytes()
    with tempfile.TemporaryDirectory() as temporary:
        expected = build.build(Path(temporary) / 'index.html', root=root).read_bytes()
    if payload != expected:
        raise ValueError('dist/index.html differs from current sources. Run python build.py first.')
    digest = hashlib.sha256(payload).hexdigest()
    directory = Path(output_dir) if output_dir else root / 'build/delivery'
    directory.mkdir(parents=True, exist_ok=True)
    filename = f'StarGuard-{digest[:12]}.html'
    target = directory / filename
    target.write_bytes(payload)
    manifest = {'file': filename, 'sha256': digest, 'size_bytes': len(payload),
                'source': 'dist/index.html', 'matches_current_sources': True}
    (directory / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    try:
        print(package(args.output_dir))
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(1, f'Delivery failed: {exc}\n')
