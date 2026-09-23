"""Keep nested substances associated with their precise mobile-phase occurrence."""

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


@pytest.fixture(scope="module")
def source():
    return SchemaView(
        str(files("nmdc_schema").joinpath("nmdc_materialized_patterns.yaml"))
    )


@pytest.mark.parametrize(
    "collection,root,concrete",
    [
        ("configuration_set", "Configuration", "ChromatographyConfiguration"),
        (
            "material_processing_set",
            "MaterialProcessing",
            "ChromatographicSeparationProcess",
        ),
    ],
)
def test_nested_substances_retain_positions_duplicates_types_and_quantities(
    source, collection, root, concrete
):
    quantity = {
        "type": "nmdc:QuantityValue",
        "has_numeric_value": 5.5,
        "has_minimum_numeric_value": 5.0,
        "has_maximum_numeric_value": 6.0,
        "has_unit": "mL",
        "has_raw_value": "5.5 mL",
    }
    substance = {
        "type": "nmdc:PortionOfSubstance",
        "known_as": "water",
        "substance_role": "solvent",
        **{
            name: deepcopy(quantity)
            for name in (
                "volume",
                "mass",
                "final_concentration",
                "source_concentration",
            )
        },
    }
    phase = {
        "type": "nmdc:MobilePhaseSegment",
        "duration": {"has_numeric_value": 2.0, "has_unit": "min"},
        "volume": deepcopy(quantity),
        "substances_used": [substance, deepcopy(substance)],
    }
    record = {
        "id": "example:one",
        "type": f"nmdc:{concrete}",
        "ordered_mobile_phases": [
            phase,
            {"type": "nmdc:MobilePhaseSegment"},
            deepcopy(phase),
        ],
    }
    original = deepcopy(record)
    phase_table = f"{collection}_ordered_mobile_phases"
    substance_table = f"{phase_table}_substances_used"
    definitions = dict(side_table_class_defs(source, root, collection))
    rows = list(side_table_rows(record, source, root, collection))
    phases = [row for table, row in rows if table == phase_table]
    substances = [row for table, row in rows if table == substance_table]

    assert record == original
    assert [row["mobile_phase_index"] for row in phases] == [0, 1, 2]
    assert [
        (row["mobile_phase_index"], row["substance_index"]) for row in substances
    ] == [(0, 0), (0, 1), (2, 0), (2, 1)]
    for table, row in rows:
        assert set(row) <= set(definitions[table].attributes)
        assert row["parent_id"] == "example:one"
        assert row["type"] == (
            "nmdc:MobilePhaseSegment"
            if table == phase_table
            else "nmdc:PortionOfSubstance"
        )
        assert all(not isinstance(value, dict) for value in row.values())
    for row in substances:
        assert row["known_as"] == "water"
        assert row["substance_role"] == "solvent"
        for name in ("volume", "mass", "final_concentration", "source_concentration"):
            for key, value in quantity.items():
                if key != "type":
                    assert row[f"{name}_{key}"] == value
    for index in ("mobile_phase_index", "substance_index"):
        slot = definitions[substance_table].attributes[index]
        assert slot.range == "integer" and slot.required and slot.minimum_value == 0
    # Root identity is part of the compound key: equal phases in another record stay distinct.
    record["id"] = "example:two"
    other = list(side_table_rows(record, source, root, collection))
    assert all(row["parent_id"] == "example:two" for _, row in other)


@pytest.mark.parametrize("value", [None, []])
def test_missing_empty_and_null_substance_lists_keep_their_phase(source, value):
    record = {
        "id": "example:configuration",
        "type": "nmdc:ChromatographyConfiguration",
        "ordered_mobile_phases": [
            {"type": "nmdc:MobilePhaseSegment"},
            {"type": "nmdc:MobilePhaseSegment", "substances_used": value},
        ],
    }
    rows = list(side_table_rows(record, source, "Configuration", "configuration_set"))
    assert len(rows) == 2
    assert all(table == "configuration_set_ordered_mobile_phases" for table, _ in rows)
    assert [row["mobile_phase_index"] for _, row in rows] == [0, 1]


@pytest.mark.parametrize("value", [None, []])
def test_empty_and_null_phase_lists_emit_no_helpers(source, value):
    record = {
        "id": "example:configuration",
        "type": "nmdc:ChromatographyConfiguration",
        "ordered_mobile_phases": value,
    }
    assert not list(
        side_table_rows(record, source, "Configuration", "configuration_set")
    )


def test_singleton_objects_keep_existing_list_coercion(source):
    record = {
        "id": "example:configuration",
        "type": "nmdc:ChromatographyConfiguration",
        "ordered_mobile_phases": {
            "type": "nmdc:MobilePhaseSegment",
            "substances_used": {"type": "nmdc:PortionOfSubstance", "known_as": "water"},
        },
    }
    rows = list(side_table_rows(record, source, "Configuration", "configuration_set"))
    assert len(rows) == 2
    assert rows[1][1]["substance_index"] == rows[1][1]["mobile_phase_index"] == 0


@pytest.mark.parametrize("value", [None, "sensitive content", 1, []])
@pytest.mark.parametrize("level", ["phase", "substance"])
def test_invalid_elements_fail_without_disclosing_input(source, value, level):
    phase = (
        value
        if level == "phase"
        else {"type": "nmdc:MobilePhaseSegment", "substances_used": [value]}
    )
    record = {
        "id": "example:configuration",
        "type": "nmdc:ChromatographyConfiguration",
        "ordered_mobile_phases": [phase],
    }
    with pytest.raises(TypeError, match="requires object list elements") as error:
        list(side_table_rows(record, source, "Configuration", "configuration_set"))
    assert "sensitive content" not in str(error.value)


@pytest.mark.parametrize(
    "override",
    [{"range": "string"}, {"multivalued": False}, {"inlined": False}],
)
def test_changed_nested_schema_shape_is_rejected_by_generator_and_runtime(override):
    source = SchemaView(
        SchemaDefinition(
            id="https://example.org/changed-phase-schema",
            name="changed_phase_schema",
            classes={
                "Root": ClassDefinition(
                    name="Root",
                    attributes={
                        "ordered_mobile_phases": SlotDefinition(
                            name="ordered_mobile_phases",
                            range="MobilePhaseSegment",
                            inlined=True,
                            multivalued=True,
                        ),
                    },
                ),
                "MobilePhaseSegment": ClassDefinition(
                    name="MobilePhaseSegment",
                    attributes={
                        "substances_used": SlotDefinition(
                            **{
                                "name": "substances_used",
                                "range": "PortionOfSubstance",
                                "inlined": True,
                                "multivalued": True,
                                **override,
                            }
                        ),
                    },
                ),
                "PortionOfSubstance": ClassDefinition(name="PortionOfSubstance"),
            },
        )
    )
    with pytest.raises(
        ValueError, match="Unsupported mobile-phase substances schema shape"
    ):
        side_table_class_defs(source, "Root", "root_set")
    with pytest.raises(
        ValueError, match="Unsupported mobile-phase substances schema shape"
    ):
        list(
            side_table_rows(
                {"id": "example:root", "ordered_mobile_phases": [{}]},
                source,
                "Root",
                "root_set",
            )
        )


@pytest.mark.parametrize("has_identifier", [False, True])
def test_unset_inlining_uses_the_range_identifier_default(
    source, monkeypatch, has_identifier
):
    original_slot = source.induced_slot
    original_identifier = source.get_identifier_slot

    def induced(name, class_name=None, **kwargs):
        slot = original_slot(name, class_name, **kwargs)
        if name == "substances_used" and class_name == "MobilePhaseSegment":
            slot = deepcopy(slot)
            slot.inlined = None
        return slot

    def identifier(class_name, **kwargs):
        if class_name == "PortionOfSubstance" and has_identifier:
            return SlotDefinition(name="id", identifier=True)
        return original_identifier(class_name, **kwargs)

    monkeypatch.setattr(source, "induced_slot", induced)
    monkeypatch.setattr(source, "get_identifier_slot", identifier)
    record = {
        "id": "example:configuration",
        "type": "nmdc:ChromatographyConfiguration",
        "ordered_mobile_phases": [{"substances_used": [{"known_as": "water"}]}],
    }
    if has_identifier:
        with pytest.raises(
            ValueError, match="Unsupported mobile-phase substances schema shape"
        ):
            side_table_class_defs(source, "Configuration", "configuration_set")
        with pytest.raises(
            ValueError, match="Unsupported mobile-phase substances schema shape"
        ):
            list(side_table_rows(record, source, "Configuration", "configuration_set"))
    else:
        definitions = dict(
            side_table_class_defs(source, "Configuration", "configuration_set")
        )
        table, row = list(
            side_table_rows(record, source, "Configuration", "configuration_set")
        )[-1]
        assert row["known_as"] == "water"
        assert set(row) <= set(definitions[table].attributes)
