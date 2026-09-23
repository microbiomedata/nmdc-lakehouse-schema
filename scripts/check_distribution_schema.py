"""Require wheel and source archives to contain the verified canonical schema bytes."""

import argparse
from pathlib import Path
import tarfile
import zipfile

from nmdc_lakehouse_schema.artifacts import SUPPORTED_SOURCE_VERSIONS, flat_schema_resource

from generate_flattened_schema import (
    CANONICAL_OUTPUT,
    check_schema_artifact,
    render_installed_schema,
    verify_content_digest,
)

RESOURCE = "nmdc_lakehouse_schema/schema/nmdc_schema_flattened.yaml"


def check_archive(path: Path, expected: bytes, resource: str = RESOURCE) -> None:
    if path.name.endswith(".whl"):
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name == resource]
            observed = archive.read(names[0]) if len(names) == 1 else None
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path) as archive:
            members = [
                member
                for member in archive.getmembers()
                if member.name.endswith(f"/src/{resource}") and member.isfile()
            ]
            if len(members) == 1:
                with archive.extractfile(members[0]) as stream:
                    observed = stream.read()
            else:
                observed = None
    else:
        raise ValueError(f"Unsupported archive: {path.name}")
    if observed is None:
        raise ValueError(f"Expected exactly one {resource} in {path.name}")
    if observed != expected:
        raise ValueError(
            f"Packaged schema differs from the checked-in artifact: {path.name}: {resource}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", type=Path, nargs="+")
    args = parser.parse_args()
    rendered = render_installed_schema()
    check_schema_artifact(CANONICAL_OUTPUT, rendered)
    verify_content_digest(rendered)
    for source_version in SUPPORTED_SOURCE_VERSIONS:
        artifact = flat_schema_resource(source_version)
        expected = artifact.read_text(encoding="utf-8")
        verify_content_digest(expected)
        relative = Path(str(artifact)).relative_to(CANONICAL_OUTPUT.parents[1]).as_posix()
        resource = f"nmdc_lakehouse_schema/{relative}"
        for path in args.archives:
            check_archive(path, expected.encode("utf-8"), resource)
            print(f"Verified source {source_version} schema in {path.name}")


if __name__ == "__main__":
    main()
