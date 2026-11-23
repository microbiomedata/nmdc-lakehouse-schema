"""A missing or stray helper table fails the release-shape check."""

import copy
from importlib.resources import files

import pytest
from linkml_runtime import SchemaView

from nmdc_lakehouse_schema.artifacts import LATEST_SOURCE_VERSION, flat_schema_resource
from tests.release_shape import assert_release_shape


@pytest.fixture(scope="module")
def source_and_classes():
    source = SchemaView(
        str(files("nmdc_schema").joinpath("nmdc_materialized_patterns.yaml"))
    )
    target = SchemaView(str(flat_schema_resource(LATEST_SOURCE_VERSION)))
    return source, target.all_classes()


def test_published_artifact_has_the_expected_helper_tables(source_and_classes):
    source, classes = source_and_classes
    assert_release_shape(classes, source)


def test_missing_helper_table_fails(source_and_classes):
    source, classes = source_and_classes
    classes = dict(classes)
    classes.pop("biosample_set_associated_studies")
    with pytest.raises(
        AssertionError, match="missing: \\['biosample_set_associated_studies'\\]"
    ):
        assert_release_shape(classes, source)


def test_stray_helper_table_fails(source_and_classes):
    source, classes = source_and_classes
    stray = copy.deepcopy(classes["biosample_set_associated_studies"])
    stray.name = "biosample_set_not_a_source_slot"
    stray.annotations["table_name"].value = stray.name
    classes = {**classes, stray.name: stray}
    with pytest.raises(
        AssertionError, match="stray: \\['biosample_set_not_a_source_slot'\\]"
    ):
        assert_release_shape(classes, source)
