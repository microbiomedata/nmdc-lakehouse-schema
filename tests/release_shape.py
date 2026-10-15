"""Check a flat schema's table set by its structure instead of a fixed count.

A source release can add or remove multivalued slots, which adds or removes
helper tables, so a hard-coded class count breaks on every schema release
without saying what changed. These checks tie every table to a primary table
and, when the source schema is available, every primary table to a
``Database`` collection.
"""


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
            if source.get_class(slot.range) is not None
        }
        assert primary == {rng: name for name, rng in collections.items()}
