"""The release gate rejects missing, duplicated, or stale packaged schema copies."""

import importlib.util
import io
from pathlib import Path
import tarfile
import zipfile

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.fixture
def checker(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "check_distribution_schema", SCRIPTS / "check_distribution_schema.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
@pytest.mark.parametrize(
    "contents",
    [[], [b"old schema"], [b"current schema"], [b"current schema", b"current schema"]],
)
def test_archive_requires_one_exact_schema(tmp_path, checker, kind, contents):
    if kind == "wheel":
        archive = tmp_path / "example.whl"
        with zipfile.ZipFile(archive, "w") as stream:
            for content in contents:
                stream.writestr(checker.RESOURCE, content)
    else:
        archive = tmp_path / "example.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            for i, content in enumerate(contents):
                member = tarfile.TarInfo(f"example-{i}/src/{checker.RESOURCE}")
                member.size = len(content)
                stream.addfile(member, io.BytesIO(content))
    if contents == [b"current schema"]:
        checker.check_archive(archive, b"current schema")
    else:
        with pytest.raises(ValueError):
            checker.check_archive(archive, b"current schema")
