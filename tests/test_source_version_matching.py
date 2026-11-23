"""Source versions select artifacts as PEP 440 releases, not as strings."""

import pytest

from nmdc_lakehouse_schema.artifacts import (
    LATEST_SOURCE_VERSION,
    SUPPORTED_SOURCE_VERSIONS,
    flat_schema_resource,
    supported_source_version,
)

# Supported releases with a zero patch, written either way ("11.24.0" or "11.25").
ZERO_PATCH = [v for v in SUPPORTED_SOURCE_VERSIONS if v.count(".") == 1 or v.endswith(".0")]


@pytest.mark.parametrize("supported", ZERO_PATCH)
def test_two_and_three_part_versions_select_the_same_artifact(supported):
    # nmdc-schema 11.25 was published on PyPI as "11.25", not "11.25.0".
    major, minor = supported.split(".")[:2]
    for form in (f"{major}.{minor}", f"{major}.{minor}.0"):
        assert supported_source_version(form) == supported
        assert flat_schema_resource(form) == flat_schema_resource(supported)


@pytest.mark.parametrize("prefix,suffix", [("v", ""), ("", " "), (" ", "")])
def test_versions_not_in_normal_form_are_refused(prefix, suffix):
    assert supported_source_version(f"{prefix}{LATEST_SOURCE_VERSION}{suffix}") is None


def test_invalid_versions_are_refused():
    assert supported_source_version("../11.24.0") is None
