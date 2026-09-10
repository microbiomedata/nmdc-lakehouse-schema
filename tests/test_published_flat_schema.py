"""The committed flattened-schema artifact is this repo's published product.

It must stay in lockstep with the generator and the pinned nmdc-schema: a fresh generation has to
reproduce the committed file byte-for-byte, and the file's self-declared content digest has to
describe its own bytes. If nmdc-schema is bumped (or the generator changes) without regenerating,
these fail — which is the signal to run `just generate-flat-schema`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/generate_flattened_schema.py"


def _load_generator_script():
    spec = importlib.util.spec_from_file_location("generate_flattened_schema", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_flat_schema_matches_a_fresh_generation() -> None:
    generator = _load_generator_script()
    expected = generator.render_installed_schema()
    # Raises SchemaArtifactError if the committed artifact is missing or differs.
    generator.check_schema_artifact(generator.CANONICAL_OUTPUT, expected)


def test_committed_flat_schema_digest_describes_its_own_bytes() -> None:
    generator = _load_generator_script()
    generator.verify_content_digest(generator.CANONICAL_OUTPUT.read_text(encoding="utf-8"))
