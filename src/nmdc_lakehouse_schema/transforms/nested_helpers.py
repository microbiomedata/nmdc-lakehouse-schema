"""The bounded contract for helper tables nested inside helper tables.

A helper table holds one row per element of a multivalued inlined slot. When
those elements carry their own multivalued inlined list, the generic flattener
would drop it. Each path listed here instead gets its own nested helper table,
with explicit list positions that tie every nested row to its parent element.
Only listed paths are supported, and a change to a listed path's shape is
refused rather than silently flattened differently.
"""

from dataclasses import dataclass

from linkml_runtime import SchemaView
from linkml_runtime.linkml_model import SlotDefinition


@dataclass(frozen=True)
class NestedHelper:
    """One supported nested list and the names its helper tables use."""

    parent_slot: str
    parent_range: str
    nested_slot: str
    nested_range: str
    label: str
    parent_index: str
    parent_index_description: str
    parent_type_error: str
    nested_index: str
    nested_index_description: str
    nested_type_error: str
    join_note: str


NESTED_HELPERS = (
    NestedHelper(
        parent_slot="ordered_mobile_phases",
        parent_range="MobilePhaseSegment",
        nested_slot="substances_used",
        nested_range="PortionOfSubstance",
        label="mobile-phase substances",
        parent_index="mobile_phase_index",
        parent_index_description=(
            "Zero-based source list position of this mobile phase within its root record."
        ),
        parent_type_error="Mobile-phase projection requires object list elements.",
        nested_index="substance_index",
        nested_index_description=(
            "Zero-based source list position of this substance within its mobile phase."
        ),
        nested_type_error="Substance projection requires object list elements.",
        join_note=(
            " Join to its mobile phase using parent_id and mobile_phase_index; "
            "substance_index preserves the source list order and duplicates."
        ),
    ),
    NestedHelper(
        parent_slot="added_isotopologs",
        parent_range="IsotopologAddition",
        nested_slot="isotope_atom_fractions",
        nested_range="IsotopologComposition",
        label="isotope atom fractions",
        parent_index="isotopolog_index",
        parent_index_description=(
            "Zero-based source list position of this isotopolog addition within its "
            "root record."
        ),
        parent_type_error="Isotopolog projection requires object list elements.",
        nested_index="isotope_atom_fraction_index",
        nested_index_description=(
            "Zero-based source list position of this isotope atom fraction within its "
            "isotopolog addition."
        ),
        nested_type_error="Isotope atom fraction projection requires object list elements.",
        join_note=(
            " Join to its isotopolog addition using parent_id and isotopolog_index. "
            "isotope_atom_fraction_index preserves the source list order and duplicates."
        ),
    ),
)


def nested_helper(schema_view: SchemaView, slot: SlotDefinition) -> NestedHelper | None:
    """Return the supported nested list under ``slot``, refusing a changed shape."""
    helper = next(
        (
            h
            for h in NESTED_HELPERS
            if slot.name == h.parent_slot and slot.range == h.parent_range
        ),
        None,
    )
    if helper is None:
        return None
    nested = schema_view.induced_slot(helper.nested_slot, helper.parent_range)
    inlined = nested.inlined
    if inlined is None and nested.range == helper.nested_range:
        inlined = schema_view.get_identifier_slot(nested.range) is None
    if not (nested.range == helper.nested_range and nested.multivalued and inlined):
        raise ValueError(f"Unsupported {helper.label} schema shape.")
    return helper
