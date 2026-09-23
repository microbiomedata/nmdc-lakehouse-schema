"""Select a published flat artifact that matches the consumer's source package."""

from importlib.resources import files

LATEST_SOURCE_VERSION = "11.24.0"
SUPPORTED_SOURCE_VERSIONS = ("11.23.0", LATEST_SOURCE_VERSION)


def flat_schema_resource(source_package_version: str):
    """Return the exact supported artifact, refusing an implicit version fallback.

    The caller supplies its installed ``nmdc-schema`` distribution version. This
    does not detect the database version or migrate records between versions.
    """
    if source_package_version not in SUPPORTED_SOURCE_VERSIONS:
        raise ValueError(
            "Unsupported NMDC source package version; select a supported source/flat pair."
        )
    relative = (
        "schema/nmdc_schema_flattened.yaml"
        if source_package_version == LATEST_SOURCE_VERSION
        else f"schema/compat/{source_package_version}/nmdc_schema_flattened.yaml"
    )
    resource = files("nmdc_lakehouse_schema").joinpath(relative)
    if not resource.is_file():
        raise FileNotFoundError("The installed package is missing its matching flat schema.")
    return resource
