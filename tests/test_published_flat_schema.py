"""The committed flattened-schema artifact is this repo's published product.

It must stay in lockstep with the generator and the pinned nmdc-schema: a fresh generation has to
reproduce the committed file byte-for-byte, and the file's self-declared content digest has to
describe its own bytes. If nmdc-schema is bumped (or the generator changes) without regenerating,
these fail — which is the signal to run `just generate-flat-schema`.
"""

from __future__ import annotations

import importlib.util
from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest

from nmdc_lakehouse_schema.artifacts import SUPPORTED_SOURCE_VERSIONS, flat_schema_resource

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


@pytest.mark.parametrize("source_version", SUPPORTED_SOURCE_VERSIONS)
def test_committed_flat_schema_digest_describes_its_own_bytes(source_version) -> None:
    generator = _load_generator_script()
    generator.verify_content_digest(flat_schema_resource(source_version).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "installed,args,message",
    [
        ("11.23.0", [], "Canonical generation requires"),
        ("11.24.0", ["--compatibility"], "Compatibility generation requires"),
        ("11.25.0", ["--compatibility"], "Compatibility generation requires"),
    ],
)
def test_cli_refuses_an_incorrect_source_before_rendering(monkeypatch, capsys, installed, args, message):
    generator = _load_generator_script()
    monkeypatch.setattr(generator, "version", lambda _package: installed)
    monkeypatch.setattr(generator, "render_installed_schema", lambda: pytest.fail("must not render"))
    with pytest.raises(SystemExit) as error:
        generator.main(args)
    assert error.value.code == 2
    assert message in capsys.readouterr().err


def test_compatibility_cannot_overwrite_canonical_artifact(monkeypatch, capsys):
    generator = _load_generator_script()
    monkeypatch.setattr(generator, "version", lambda _package: "11.23.0")
    with pytest.raises(SystemExit) as error:
        generator.main(["--compatibility", str(generator.CANONICAL_OUTPUT)])
    assert error.value.code == 2
    assert "cannot overwrite the canonical artifact" in capsys.readouterr().err


def test_stale_compatibility_artifact_names_the_compatibility_recipe(tmp_path, monkeypatch, capsys):
    generator = _load_generator_script()
    monkeypatch.setattr(generator, "version", lambda _package: "11.23.0")
    monkeypatch.setattr(generator, "render_installed_schema", lambda: "regenerated artifact")
    output = tmp_path / "stale.yaml"
    output.write_text("older artifact")
    with pytest.raises(SystemExit) as error:
        generator.main(["--compatibility", "--check", str(output)])
    assert error.value.code == 2
    message = capsys.readouterr().err
    assert "just generate-compat-schema" in message
    assert "just generate-flat-schema" not in message


@pytest.mark.parametrize("args", [[], ["--compatibility"]])
def test_missing_source_distribution_is_a_clean_cli_error(monkeypatch, capsys, args):
    generator = _load_generator_script()

    def missing(_package):
        raise PackageNotFoundError("nmdc-schema")

    monkeypatch.setattr(generator, "version", missing)
    with pytest.raises(SystemExit) as error:
        generator.main(args)
    assert error.value.code == 2
    message = capsys.readouterr().err
    assert "nmdc-schema package is not installed" in message
    assert "Traceback" not in message
