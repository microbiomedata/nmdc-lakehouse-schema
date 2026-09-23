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
      type:
      label:
        range: TextValue
  SpecialInner:
    is_a: Inner
    attributes:
      extra_text:
        range: TextValue
        required: true
      extra_scalar:
        required: true
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
  SpecialDetail:
    is_a: Detail
    attributes:
      extra_text:
        range: TextValue
        required: true
      extra_scalar:
        required: true
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


@pytest.mark.parametrize("detail_class", ["Detail", "SpecialDetail"])
@pytest.mark.parametrize("inner_class", ["Inner", "SpecialInner"])
@pytest.mark.parametrize("placement", ["primary", "child"])
def test_embedded_subtype_columns_match_runtime_at_both_levels(
    sv, detail_class, inner_class, placement
):
    detail = {
        "type": f"test:{detail_class}",
        "label": {"has_raw_value": "detail"},
        "inner": {"type": f"test:{inner_class}", "label": {"has_raw_value": "inner"}},
    }
    expected = {"label": "detail", "inner_label": "inner"}
    for obj, class_name, prefix in (
        (detail, detail_class, ""),
        (detail["inner"], inner_class, "inner_"),
    ):
        if class_name.startswith("Special"):
            obj.update(extra_text={"has_raw_value": "projected"}, extra_scalar="scalar")
            expected.update(
                {f"{prefix}extra_text": "projected", f"{prefix}extra_scalar": "scalar"}
            )
    if placement == "primary":
        row = flatten_record({"detail": detail}, sv, "Record")
        flat = flatten_class_def(sv, "Record")
        prefix = "detail_"
        expected = {f"{prefix}{key}": value for key, value in expected.items()}
    else:
        record = {"id": "synthetic:1", "children": [detail]}
        [(table, row)] = side_table_rows(record, sv, "Record", "record_set")
        flat = dict(side_table_class_defs(sv, "Record", "record_set"))[table]
        prefix = ""
        expected.update(parent_id="synthetic:1", type=f"test:{detail_class}")

    assert row == expected
    assert row.keys() <= flat.attributes.keys()
    for level, subclass in (("", "SpecialDetail"), ("inner_", "SpecialInner")):
        for name in ("extra_text", "extra_scalar"):
            attribute = flat.attributes[f"{prefix}{level}{name}"]
            assert attribute.range == "string"
            assert attribute.required is False
            assert subclass in attribute.description
    # Shared columns keep their base definitions when subclasses inherit them.
    assert "Polymorphic" not in flat.attributes[f"{prefix}label"].description


def test_repeated_textvalues_are_parent_strings_without_a_child_table(sv):
    values = [
        {"has_raw_value": v, "type": "nmdc:TextValue"} for v in ("one", "one", "", None)
    ]
    record = {"id": "synthetic:1", "type": "test:Record", "texts": values}
    assert flatten_record(record, sv, "Record") == {
        "id": "synthetic:1",
        "type": "test:Record",
        "texts": ["one", "one", "", None],
    }
    assert list(side_table_rows(record, sv, "Record", "record_set")) == []
    flat = flatten_database_schema(sv)
    assert "record_set_texts" not in flat.classes
    attribute = flat.classes["RecordFlat"].attributes["texts"]
    assert attribute.range == "string"
    assert attribute.multivalued is True
    assert "texts.has_raw_value" in attribute.description


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
    expected = {"texts": []} if value == [] else {}
    assert flatten_record({"texts": value}, sv, "Record") == expected
    assert (
        list(
            side_table_rows(
                {"id": "synthetic:1", "texts": value}, sv, "Record", "record_set"
            )
        )
        == []
    )


def test_single_object_in_multivalued_slot_is_one_parent_array_element(sv):
    record = {"id": "synthetic:1", "texts": {"has_raw_value": "one"}}
    assert flatten_record(record, sv, "Record") == {
        "id": "synthetic:1",
        "texts": ["one"],
    }
    assert list(side_table_rows(record, sv, "Record", "record_set")) == []


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
        if placement == "child":
            list(side_table_rows(record, sv, "Record", "record_set"))
        else:
            flatten_record(record, sv, "Record")
    assert "sensitive" not in str(error.value)


@pytest.mark.parametrize(
    ("class_name", "slot_name"),
    [
        ("Detail", "label"),
        ("Inner", "label"),
        ("SpecialDetail", "extra_text"),
        ("SpecialInner", "extra_text"),
    ],
)
@pytest.mark.parametrize("placement", ["primary", "child"])
def test_nested_multivalued_textvalues_are_columns_on_the_containing_record(
    sv, class_name, slot_name, placement
):
    sv.schema.classes[class_name].attributes[slot_name].multivalued = True
    sv.set_modified()
    expected = ["one", "one", "", None]
    value = {
        "type": f"test:{class_name}",
        slot_name: [{"has_raw_value": text} for text in expected],
    }
    detail = {"inner": value} if class_name.endswith("Inner") else value
    column = f"inner_{slot_name}" if class_name.endswith("Inner") else slot_name
    if placement == "primary":
        row = flatten_record({"detail": detail}, sv, "Record")
        flat = flatten_class_def(sv, "Record")
        column = f"detail_{column}"
    else:
        record = {"id": "synthetic:1", "children": [detail]}
        [(table, row)] = side_table_rows(record, sv, "Record", "record_set")
        flat = dict(side_table_class_defs(sv, "Record", "record_set"))[table]
    assert row[column] == expected
    assert row.keys() <= flat.attributes.keys()
    assert flat.attributes[column].range == "string"
    assert flat.attributes[column].multivalued is True


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
            else:
                single += 1
            assert f"{collection.name}_{slot.name}" not in flat.classes
            attribute = primary.attributes[slot.name]
            assert f"{slot.name}_has_raw_value" not in primary.attributes
            assert f"{slot.name}_language" not in primary.attributes
            assert attribute.range == "string"
            assert attribute.multivalued == bool(slot.multivalued)
    assert (single, repeated) == (101, 41)
    assert len(flat.classes) == 61
    assert "biosample_set_host_diet" not in flat.classes
    assert flat.classes["BiosampleFlat"].attributes["host_diet"].multivalued is True
