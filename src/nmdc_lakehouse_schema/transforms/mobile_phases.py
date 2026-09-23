"""The bounded nested-helper contract for mobile-phase substances."""

from linkml_runtime import SchemaView
from linkml_runtime.linkml_model import SlotDefinition


def substance_range(schema_view: SchemaView, slot: SlotDefinition) -> str | None:
    """Recognize the supported path and refuse changes to its nested shape."""
    if slot.name != "ordered_mobile_phases" or slot.range != "MobilePhaseSegment":
        return None
    nested = schema_view.induced_slot("substances_used", "MobilePhaseSegment")
    if not (
        nested.range == "PortionOfSubstance" and nested.multivalued and nested.inlined
    ):
        raise ValueError("Unsupported mobile-phase substances schema shape.")
    return nested.range
