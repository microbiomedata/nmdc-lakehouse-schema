"""Select a published flat artifact that matches the consumer's source package."""

from importlib.resources import files

from packaging.version import InvalidVersion, Version

LATEST_SOURCE_VERSION = "11.24.0"
SUPPORTED_SOURCE_VERSIONS = ("11.23.0", LATEST_SOURCE_VERSION)


def supported_source_version(source_package_version: str) -> str | None:
    """Return the supported version naming the same PEP 440 release, if any.

    nmdc-schema 11.25 was published as ``11.25``, so ``11.25`` and ``11.25.0``
    must select the same artifact. Only versions already in normal form match:
    ``v11.24.0`` or ``11.24.0 `` are refused rather than normalized.
    """
    try:
        requested = Version(source_package_version)
    except InvalidVersion:
        return None
    if str(requested) != source_package_version:
        return None
    return next((supported for supported in SUPPORTED_SOURCE_VERSIONS if Version(supported) == requested), None)


def flat_schema_resource(source_package_version: str):
    """Return the exact supported artifact, refusing an implicit version fallback.

    The caller supplies its installed ``nmdc-schema`` distribution version. This
    does not detect the database version or migrate records between versions.
    """
    supported = supported_source_version(source_package_version)
    if supported is None:
        raise ValueError(
            "Unsupported NMDC source package version; select a supported source/flat pair."
        )
    relative = (
        "schema/nmdc_schema_flattened.yaml"
        if supported == LATEST_SOURCE_VERSION
        else f"schema/compat/{supported}/nmdc_schema_flattened.yaml"
    )
    resource = files("nmdc_lakehouse_schema").joinpath(relative)
    if not resource.is_file():
        raise FileNotFoundError("The installed package is missing its matching flat schema.")
    return resource
