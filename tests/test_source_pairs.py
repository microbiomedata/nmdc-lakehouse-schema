"""Supported releases retain their own source fields under one projection."""

from importlib.metadata import version
from importlib.resources import files

import pytest
from linkml_runtime import SchemaView

from nmdc_lakehouse_schema.artifacts import (
    SUPPORTED_SOURCE_VERSIONS,
    flat_schema_resource,
)
from nmdc_lakehouse_schema.transforms.flatteners import flatten_record, side_table_rows
from nmdc_lakehouse_schema.transforms.schema_generator import FLATTENER_VERSION


@pytest.mark.parametrize("source_version", SUPPORTED_SOURCE_VERSIONS)
def test_resource_selects_exact_source_and_projection(source_version):
    target = SchemaView(str(flat_schema_resource(source_version)))
    assert target.schema.annotations["source_package_version"].value == source_version
    assert target.schema.version == f"{source_version}+flat.{FLATTENER_VERSION}"
    # DataGeneration gained credit associations (and their helper) in 11.24.0.
    assert len(target.all_classes()) == (60 if source_version == "11.23.0" else 61)
    assert "configuration_set_ordered_mobile_phases_substances_used" in target.all_classes()
    biosample = target.get_class("BiosampleFlat")
    assert biosample.attributes["host_diet"].range == "string"
    assert biosample.attributes["host_diet"].multivalued


@pytest.mark.parametrize("source_version", ["11.22.0", "11.25.0", "v11.24.0", "../11.24.0", ""])
def test_unsupported_versions_do_not_fall_back(source_version):
    with pytest.raises(ValueError, match="Unsupported NMDC source package version"):
        flat_schema_resource(source_version)


def test_current_source_runtime_preserves_textvalues_and_source_specific_credit_fields():
    installed = version("nmdc-schema")
    source = SchemaView(str(files("nmdc_schema").joinpath("nmdc_materialized_patterns.yaml")))
    target = SchemaView(str(flat_schema_resource(installed)))
    biosample = flatten_record(
        {"type": "nmdc:Biosample", "host_diet": [{"type": "nmdc:TextValue", "has_raw_value": "fruit"}]},
        source,
        "Biosample",
    )
    assert biosample["host_diet"] == ["fruit"]
    legacy = installed == "11.23.0"
    person_slot = "applies_to_person" if legacy else "applies_to_agent"
    person_type = "nmdc:PersonValue" if legacy else "nmdc:Person"
    person = {"type": person_type, "name": "Example Researcher", "orcid": "orcid:0000-0001-2345-6789"}
    record = {
        "id": "example:study",
        "type": "nmdc:Study",
        "has_credit_associations": [{"type": "prov:Association", person_slot: person}],
    }
    if legacy:
        person["has_raw_value"] = "Example Researcher"
        record["principal_investigator"] = person
    flat = flatten_record(record, source, "Study")
    if legacy:
        assert flat["principal_investigator_name"] == person["name"]
        assert flat["principal_investigator_has_raw_value"] == person["has_raw_value"]
        assert "principal_investigator_name" in target.get_class("StudyFlat").attributes
    else:
        assert "principal_investigator_name" not in target.get_class("StudyFlat").attributes
    table, row = next(side_table_rows(record, source, "Study", "study_set"))
    assert table == "study_set_has_credit_associations"
    assert row[f"{person_slot}_name"] == person["name"]
    assert row[f"{person_slot}_orcid"] == person["orcid"]
    if legacy:
        assert row[f"{person_slot}_has_raw_value"] == person["has_raw_value"]
    assert set(row) <= set(target.get_class(table).attributes)
