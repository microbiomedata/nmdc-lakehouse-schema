"""Check a flat schema's table set by its structure instead of a fixed count.

A source release can add or remove multivalued slots, which adds or removes
helper tables, so a hard-coded class count breaks on every schema release
without saying what changed. These checks tie every table to a primary table
and, when the source schema is available, every primary table to a
``Database`` collection and the full helper table set to the one the source
schema implies, so a missing or stray table still fails.
"""

# The nested helpers the flattener supports, written out here rather than
# imported, so the check stays independent of the flattener.
NESTED_HELPERS = {
    ("MobilePhaseSegment", "ordered_mobile_phases"): "substances_used",
    ("IsotopologAddition", "added_isotopologs"): "isotope_atom_fractions",
}


def _annotation(cls, tag):
    return cls.annotations[tag].value


def assert_release_shape(classes, source=None):
    """Assert every flat class is a primary table or a helper of one.

    ``classes`` maps class names to flat class definitions. With ``source``
    (the ``SchemaView`` the flat schema was generated from), also assert there
    is exactly one primary table per ``Database`` collection.
    """
    primary = {
        _annotation(cls, "source_class"): _annotation(cls, "table_name")
        for name, cls in classes.items()
        if name.endswith("Flat")
    }
    assert primary, "no primary tables"
    assert len(set(primary.values())) == len(primary)
    for name, cls in classes.items():
        if name.endswith("Flat"):
            assert name == f"{_annotation(cls, 'source_class')}Flat"
            continue
        table = _annotation(cls, "table_name")
        parent = primary.get(_annotation(cls, "source_class"))
        assert table == name
        assert parent is not None and table.startswith(f"{parent}_"), name
    if source is not None:
        collections = {
            slot.name: slot.range
            for slot in source.class_induced_slots("Database")
            if slot.multivalued and source.get_class(slot.range) is not None
        }
        assert primary == {rng: name for name, rng in collections.items()}
        helpers = {name for name in classes if not name.endswith("Flat")}
        expected = expected_helper_tables(source, collections)
        assert helpers == expected, (
            f"missing: {sorted(expected - helpers)}, stray: {sorted(helpers - expected)}"
        )


def expected_helper_tables(source, collections):
    """Name every helper table the source schema implies, without the flattener.

    A collection gets one helper per multivalued class-range slot (other than
    TextValue) on its range class or any descendant. This rule is written out
    here instead of calling the flattener, so a flattener that drops or
    invents a helper table fails this check.
    """
    expected = set()
    for collection, root in collections.items():
        for class_name in source.class_descendants(root):
            for slot in source.class_induced_slots(class_name):
                if not slot.multivalued or slot.range == "TextValue":
                    continue
                if source.get_class(slot.range) is None:
                    continue
                table = f"{collection}_{slot.name}"
                expected.add(table)
                nested = NESTED_HELPERS.get((slot.range, slot.name))
                if nested is not None:
                    expected.add(f"{table}_{nested}")
    return expected
