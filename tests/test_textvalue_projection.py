"""TextValue extraction preserves strings, multiplicity, and record discriminators."""

from importlib.util import find_spec
from pathlib import Path

import pytest
from linkml_runtime import SchemaView

from nmdc_lakehouse_schema.transforms.flatteners import flatten_record, side_table_rows
from nmdc_lakehouse_schema.transforms.schema_generator import (
    flatten_class_def,
    flatten_database_schema,
    side_table_class_defs,
)

SCHEMA = """
id: https://example.org/text-projection
name: text_projection
prefixes:
  linkml: https://w3id.org/linkml/
imports: [linkml:types]
default_range: string
classes:
  TextValue:
    attributes:
      has_raw_value:
      language:
      type:
  QuantityValue:
    attributes:
      has_raw_value:
      has_numeric_value:
        range: float
      type:
  Inner:
    attributes:
      label:
        range: TextValue
  Detail:
    attributes:
      type:
        required: true
      label:
        range: TextValue
        required: true
        description: A useful label.
      inner:
        range: Inner
  Record:
    attributes:
      id:
        identifier: true
        required: true
      type:
        required: true
        designates_type: true
      text:
        range: TextValue
        required: true
        description: A useful description.
      texts:
        range: TextValue
        multivalued: true
      quantity:
        range: QuantityValue
      detail:
        range: Detail
      children:
        range: Detail
        multivalued: true
  SpecialRecord:
    is_a: Record
    attributes:
      special_text:
        range: TextValue
        required: true
  Database:
    attributes:
      record_set:
        range: Record
        multivalued: true
"""


@pytest.fixture
def sv():
    return SchemaView(SCHEMA)


def test_primary_and_child_rows_match_schema_and_keep_record_types(sv):
    record = {
        "id": "synthetic:1",
        "type": "test:SpecialRecord",
        "text": {"has_raw_value": "a|b;\nλ", "type": "nmdc:TextValue"},
        "special_text": {"has_raw_value": "subclass"},
        "quantity": {"has_raw_value": "2 m", "has_numeric_value": 2.0},
        "detail": {
            "label": {"has_raw_value": "nested"},
            "inner": {"label": {"has_raw_value": "deep"}},
        },
        "children": [{"type": "test:Detail", "label": {"has_raw_value": "child"}}],
    }
    primary = flatten_record(record, sv, "Record")
    assert primary == {
        "id": "synthetic:1",
        "type": "test:SpecialRecord",
        "text": "a|b;\nλ",
        "special_text": "subclass",
        "quantity_has_raw_value": "2 m",
        "quantity_has_numeric_value": 2.0,
        "detail_label": "nested",
        "detail_inner_label": "deep",
    }
    flat = flatten_class_def(sv, "Record")
    assert primary.keys() <= flat.attributes.keys()
    assert flat.attributes["text"].range == "string"
    assert flat.attributes["text"].required is True
    assert "A useful description." in flat.attributes["text"].description
    assert "text.has_raw_value" in flat.attributes["text"].description
    assert flat.attributes["special_text"].required is False
    assert flat.attributes["detail_label"].required is False
    assert "A useful label." in flat.attributes["detail_label"].description
    assert "detail.label.has_raw_value" in flat.attributes["detail_label"].description
    assert flat.attributes["type"].required is True
    assert flat.attributes["type"].designates_type is not True
    assert not any(name.endswith("_language") for name in flat.attributes)
    rows = list(side_table_rows(record, sv, "Record", "record_set"))
    assert rows == [
        (
            "record_set_children",
            {"parent_id": "synthetic:1", "type": "test:Detail", "label": "child"},
        )
    ]
    child_schema = dict(side_table_class_defs(sv, "Record", "record_set"))[
        "record_set_children"
    ]
    assert rows[0][1].keys() <= child_schema.attributes.keys()
    assert child_schema.attributes["label"].range == "string"
    assert "type" in child_schema.attributes


def test_repeated_textvalues_keep_every_occurrence_and_null_row(sv):
    values = [
        {"has_raw_value": v, "type": "nmdc:TextValue"} for v in ("one", "one", "", None)
    ]
    record = {"id": "synthetic:1", "type": "test:Record", "texts": values}
    assert "texts" not in flatten_record(record, sv, "Record")
    rows = list(side_table_rows(record, sv, "Record", "record_set"))
    assert rows == [
        ("record_set_texts", {"parent_id": "synthetic:1", "texts": "one"}),
        ("record_set_texts", {"parent_id": "synthetic:1", "texts": "one"}),
        ("record_set_texts", {"parent_id": "synthetic:1", "texts": ""}),
        ("record_set_texts", {"parent_id": "synthetic:1"}),
    ]
    child = dict(side_table_class_defs(sv, "Record", "record_set"))["record_set_texts"]
    assert set(child.attributes) == {"parent_id", "texts"}
    assert child.attributes["texts"].range == "string"
    assert child.attributes["texts"].multivalued is False
    assert "texts.has_raw_value" in child.attributes["texts"].description


@pytest.mark.parametrize("value", [None, {}, {"has_raw_value": None}])
def test_absent_or_null_raw_values_are_omitted(sv, value):
    assert flatten_record({"text": value}, sv, "Record") == {}
    assert flatten_record({}, sv, "Record") == {}


def test_empty_string_and_unpopulated_extra_fields_are_allowed(sv):
    record = {
        "text": {
            "has_raw_value": "",
            "language": None,
            "extra": [],
            "empty": {},
            "type": "",
        }
    }
    assert flatten_record(record, sv, "Record") == {"text": ""}


@pytest.mark.parametrize("value", [[], None])
def test_empty_multivalued_slot_emits_no_rows(sv, value):
    assert (
        list(
            side_table_rows(
                {"id": "synthetic:1", "texts": value}, sv, "Record", "record_set"
            )
        )
        == []
    )


def test_single_object_in_multivalued_slot_is_one_string_row(sv):
    rows = list(
        side_table_rows(
            {"id": "synthetic:1", "texts": {"has_raw_value": "one"}},
            sv,
            "Record",
            "record_set",
        )
    )
    assert rows == [("record_set_texts", {"parent_id": "synthetic:1", "texts": "one"})]


@pytest.mark.parametrize(
    "value",
    [
        "sensitive-scalar",
        [],
        {"has_raw_value": 0},
        {"has_raw_value": False},
        {"has_raw_value": ["sensitive-value"]},
        {"has_raw_value": "sensitive-value", "language": "sensitive-language"},
        {
            "has_raw_value": "sensitive-value",
            "sensitive-field": {"nested": "sensitive-content"},
        },
        {"has_raw_value": "sensitive-value", "extra": 0},
        {"has_raw_value": "sensitive-value", "extra": False},
        {"has_raw_value": "sensitive-value", "type": "sensitive-type"},
    ],
)
@pytest.mark.parametrize(
    "placement", ["primary", "nested", "deep", "repeated", "child"]
)
def test_unsafe_projection_fails_without_disclosing_values(sv, value, placement):
    record = {"id": "synthetic:1"}
    if placement == "primary":
        record["text"] = value
    elif placement == "nested":
        record["detail"] = {"label": value}
    elif placement == "deep":
        record["detail"] = {"inner": {"label": value}}
    elif placement == "repeated":
        record["texts"] = [value]
    else:
        record["children"] = [{"label": value}]
    with pytest.raises(ValueError, match="TextValue") as error:
        if placement in ("repeated", "child"):
            list(side_table_rows(record, sv, "Record", "record_set"))
        else:
            flatten_record(record, sv, "Record")
    assert "sensitive" not in str(error.value)


def test_nested_multivalued_textvalues_are_not_silently_dropped(sv):
    # This shape is absent from nmdc-schema 11.23.0 and needs a separate mapping.
    sv.schema.classes["Detail"].attributes["label"].multivalued = True
    sv.set_modified()
    with pytest.raises(ValueError, match="child-table mapping"):
        flatten_class_def(sv, "Record")
    with pytest.raises(ValueError, match="child-table mapping"):
        flatten_record({"detail": {"label": [{"has_raw_value": "one"}]}}, sv, "Record")


def test_all_pinned_nmdc_textvalue_paths_have_string_columns_and_keep_primary_types():
    spec = find_spec("nmdc_schema")
    source = SchemaView(
        str(Path(spec.origin).parent / "nmdc_materialized_patterns.yaml")
    )
    flat = flatten_database_schema(source)
    single = repeated = 0
    for collection in source.class_induced_slots("Database"):
        root = source.get_class(collection.range)
        if root is None:
            continue
        primary = flat.classes[f"{root.name}Flat"]
        assert primary.attributes["type"].required is True
        slots = {
            s.name: s
            for c in source.class_descendants(root.name)
            for s in source.class_induced_slots(c)
        }
        for slot in slots.values():
            if slot.range != "TextValue":
                continue
            if slot.multivalued:
                repeated += 1
                child = flat.classes[f"{collection.name}_{slot.name}"]
                assert set(child.attributes) == {"parent_id", slot.name}
                attribute = child.attributes[slot.name]
            else:
                single += 1
                attribute = primary.attributes[slot.name]
                assert f"{slot.name}_has_raw_value" not in primary.attributes
                assert f"{slot.name}_language" not in primary.attributes
            assert attribute.range == "string"
            assert attribute.multivalued is False
    assert (single, repeated) == (101, 41)
