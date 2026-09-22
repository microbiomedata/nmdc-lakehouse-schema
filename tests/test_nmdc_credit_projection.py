"""Exercise the released 11.24.0 Agent shapes through real collection helpers."""

from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path

import pytest
from linkml_runtime import SchemaView

from nmdc_lakehouse_schema.transforms.flatteners import flatten_record, side_table_rows
from nmdc_lakehouse_schema.transforms.schema_generator import flatten_database_schema


@pytest.fixture(scope="module")
def source_and_target():
    source = SchemaView(
        str(
            Path(find_spec("nmdc_schema").origin).parent
            / "nmdc_materialized_patterns.yaml"
        )
    )
    assert version("nmdc-schema") == source.schema.version == "11.24.0"
    return source, flatten_database_schema(
        source, source_package_version=version("nmdc-schema")
    )


@pytest.mark.parametrize(
    "root,concrete,collection",
    [
        ("Study", "Study", "study_set"),
        ("DataGeneration", "MassSpectrometry", "data_generation_set"),
        ("DataGeneration", "NucleotideSequencing", "data_generation_set"),
    ],
)
def test_credit_subtype_fields_survive_in_collection_helpers(
    source_and_target, root, concrete, collection
):
    source, target = source_and_target
    agents = [
        {
            "type": "nmdc:Person",
            "name": "Synthetic person",
            "email": "person@example.org",
            "orcid": "orcid:0000-0002-1825-0097",
        },
        {
            "type": "nmdc:Organization",
            "name": "Synthetic organization",
            "ror": "ror:02jbv0t02",
        },
    ]
    record = {
        "id": "example:record",
        "type": f"nmdc:{concrete}",
        "has_credit_associations": [
            {
                "type": "nmdc:CreditAssociation",
                "applies_to_agent": agent,
                "applied_roles": ["Investigation"],
            }
            for agent in agents
        ],
    }
    assert flatten_record(record, source, root)["type"] == record["type"]
    rows = list(side_table_rows(record, source, root, collection))
    assert len(rows) == 2
    for (table, row), agent in zip(rows, agents):
        assert table == f"{collection}_has_credit_associations"
        columns = target.classes[table].attributes
        assert row.keys() <= columns.keys()
        assert row["parent_id"] == record["id"]
        assert row["type"] == "nmdc:CreditAssociation"
        assert row["applied_roles"] == ["Investigation"]
        for field, value in agent.items():
            if field != "type":
                assert row[f"applies_to_agent_{field}"] == value
        for field in ("email", "orcid", "ror"):
            assert columns[f"applies_to_agent_{field}"].range == "string"
            assert not columns[f"applies_to_agent_{field}"].required
        assert not any(name.startswith("applies_to_person_") for name in columns)


def test_release_shape_removes_retired_fields_and_adds_data_generation_credits(
    source_and_target,
):
    _, target = source_and_target
    assert target.version == "11.24.0+flat.1.2.0"
    assert len(target.classes) == 59
    assert "data_generation_set_has_credit_associations" in target.classes
    assert "collection_date_inc" not in target.classes["BiosampleFlat"].attributes
    for name in ("StudyFlat", "DataGenerationFlat"):
        assert not any(
            column.startswith("principal_investigator_")
            for column in target.classes[name].attributes
        )
