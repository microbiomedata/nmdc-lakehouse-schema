"""Data model package for nmdc-lakehouse-schema."""

from pathlib import Path
from .nmdc_lakehouse_schema import *  # noqa: F403

THIS_PATH = Path(__file__).parent

SCHEMA_DIRECTORY = THIS_PATH.parent / "schema"
MAIN_SCHEMA_PATH = SCHEMA_DIRECTORY / "nmdc_lakehouse_schema.yaml"
