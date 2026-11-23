"""Keep isotope atom fractions associated with their isotopolog addition."""

from copy import deepcopy
from importlib.resources import files

import pytest
from linkml_runtime import SchemaView
from linkml_runtime.linkml_model import (
    ClassDefinition,
    SchemaDefinition,
    SlotDefinition,
)

from nmdc_lakehouse_schema.transforms.flatteners import side_table_rows
from nmdc_lakehouse_schema.transforms.schema_generator import side_table_class_defs

ADDITIONS = "material_processing_set_added_isotopologs"
FRACTIONS = f"{ADDITIONS}_isotope_atom_fractions"


@pytest.fixture(scope="module")
def source():
    view = SchemaView(
        str(files("nmdc_schema").joinpath("nmdc_materialized_patterns.yaml"))
    )
    if view.get_class("IsotopologAddition") is None:
        pytest.skip("The installed nmdc-schema has no isotopolog additions.")
    return view


def _fraction(isotope, value):
    # Shape taken from nmdc-schema v11.26.0 src/data/valid/IsotopologAddition.yaml.
    return {
        "isotope": isotope,
        "type": "nmdc:IsotopologComposition",
        "isotopolog_atom_frac": {
            "type": "nmdc:QuantityValue",
            "has_raw_value": str(value),
            "has_numeric_value": value,
            "has_unit": "1",
        },
    }


def test_isotope_atom_fractions_retain_positions_duplicates_and_values(source):
    addition = {
        "isotopolog_label": "isotopically labeled",
        "isotope_atom_fractions": [_fraction("13C", 0.99), _fraction("13C", 0.99)],
        "type": "nmdc:IsotopologAddition",
        "isotopolog": "toluene",
    }
    record = {
        "id": "example:labeling",
        "type": "nmdc:IsotopeLabelingProcess",
        "added_isotopologs": [
            addition,
            {"type": "nmdc:IsotopologAddition", "isotopolog": "water"},
            deepcopy(addition),
        ],
    }
    original = deepcopy(record)
    definitions = dict(
        side_table_class_defs(source, "MaterialProcessing", "material_processing_set")
    )
    rows = list(
        side_table_rows(record, source, "MaterialProcessing", "material_processing_set")
    )
    additions = [row for table, row in rows if table == ADDITIONS]
    fractions = [row for table, row in rows if table == FRACTIONS]

    assert record == original
    assert [row["isotopolog_index"] for row in additions] == [0, 1, 2]
    assert [
        (row["isotopolog_index"], row["isotope_atom_fraction_index"])
        for row in fractions
    ] == [(0, 0), (0, 1), (2, 0), (2, 1)]
    for table, row in rows:
        assert set(row) <= set(definitions[table].attributes)
        assert row["parent_id"] == "example:labeling"
        assert all(not isinstance(value, dict) for value in row.values())
    for row in fractions:
        assert row["isotope"] == "13C"
        assert row["isotopolog_atom_frac_has_numeric_value"] == 0.99
        assert row["isotopolog_atom_frac_has_unit"] == "1"
        assert row["type"] == "nmdc:IsotopologComposition"
    for index in ("isotopolog_index", "isotope_atom_fraction_index"):
        slot = definitions[FRACTIONS].attributes[index]
        assert slot.range == "integer" and slot.required and slot.minimum_value == 0


def test_non_object_isotope_atom_fraction_is_refused(source):
    record = {
        "id": "example:labeling",
        "type": "nmdc:IsotopeLabelingProcess",
        "added_isotopologs": [{"isotope_atom_fractions": ["13C"]}],
    }
    with pytest.raises(TypeError, match="requires object list elements"):
        list(
            side_table_rows(
                record, source, "MaterialProcessing", "material_processing_set"
            )
        )


@pytest.mark.parametrize(
    "override",
    [{"range": "string"}, {"multivalued": False}, {"inlined": False}],
)
def test_changed_isotopolog_shape_is_rejected_by_generator_and_runtime(override):
    source = SchemaView(
        SchemaDefinition(
            id="https://example.org/changed-isotopolog-schema",
            name="changed_isotopolog_schema",
            classes={
                "Root": ClassDefinition(
                    name="Root",
                    attributes={
                        "added_isotopologs": SlotDefinition(
                            name="added_isotopologs",
                            range="IsotopologAddition",
                            inlined=True,
                            multivalued=True,
                        ),
                    },
                ),
                "IsotopologAddition": ClassDefinition(
                    name="IsotopologAddition",
                    attributes={
                        "isotope_atom_fractions": SlotDefinition(
                            **{
                                "name": "isotope_atom_fractions",
                                "range": "IsotopologComposition",
                                "inlined": True,
                                "multivalued": True,
                                **override,
                            }
                        ),
                    },
                ),
                "IsotopologComposition": ClassDefinition(name="IsotopologComposition"),
            },
        )
    )
    with pytest.raises(
        ValueError, match="Unsupported isotope atom fractions schema shape"
    ):
        side_table_class_defs(source, "Root", "root_set")
    with pytest.raises(
        ValueError, match="Unsupported isotope atom fractions schema shape"
    ):
        list(
            side_table_rows(
                {"id": "example:root", "added_isotopologs": [{}]},
                source,
                "Root",
                "root_set",
            )
        )
