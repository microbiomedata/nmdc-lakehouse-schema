# Nested mobile-phase substances

Projection **1.3.0** preserves `ordered_mobile_phases[*].substances_used[*]`
in `configuration_set` and `material_processing_set`. Source schema 11.24.0
produces target `11.24.0+flat.1.3.0`, with **61 tables**: 19 primary and 42 helpers.
This is an explicit transformation for MobilePhaseSegment and PortionOfSubstance,
not a general recursive helper-table rule.

## Tables and occurrence keys

For each collection, the existing `<collection>_ordered_mobile_phases` helper
gains a required integer `mobile_phase_index`. The new
`<collection>_ordered_mobile_phases_substances_used` helper contains:

- `parent_id`: the original collection record's identifier.
- `mobile_phase_index`: the phase's zero-based position in `ordered_mobile_phases`.
- `substance_index`: the substance's zero-based position in that phase's
  `substances_used` list.
- The substance's own `type`, `known_as`, `substance_role`, and flattened
  `final_concentration`, `source_concentration`, `mass`, and `volume` fields.

QuantityValue members retain their numeric value, minimum, maximum, unit, and
raw text. As with other single embedded wrappers, the quantity's own `type`
does not become a column. Mobile-phase and substance record types are retained.

The phase key is `(parent_id, mobile_phase_index)`. The substance key is
`(parent_id, mobile_phase_index, substance_index)`. Equal objects at different
positions remain separate occurrences; positions are local to their root
record and list, not globally unique IDs. Join on both phase-key columns:

```sql
SELECT p.parent_id, p.mobile_phase_index, s.substance_index,
       s.known_as, s.volume_has_numeric_value, s.volume_has_unit
FROM configuration_set_ordered_mobile_phases AS p
JOIN configuration_set_ordered_mobile_phases_substances_used AS s
  ON s.parent_id = p.parent_id
 AND s.mobile_phase_index = p.mobile_phase_index
ORDER BY p.parent_id, p.mobile_phase_index, s.substance_index;
```

Using only `parent_id` would associate every substance with every phase in the
same root record. Neither file row order nor substance content replaces the
explicit occurrence keys.

## Empty values and validation

Missing, null, and empty substance lists produce no substance rows; the
containing phase still has a row and an index. Missing, null, and empty phase
lists produce no phase rows. A singleton object is treated as a one-element
list, consistent with the existing helper behavior. These representations do
not preserve the distinction between an absent list, null, and an empty list.

Non-object elements, including null elements inside a populated list, raise a
`TypeError` rather than disappearing. Diagnostics do not include source values.
Root records still need an `id` to emit helpers. Other nested class paths retain
the [documented limits](transformation-support.md).

## Migration and release order

Projection 1.2.0 omitted the nested substance objects. Existing snapshots cannot
recover them from their Parquet files; a new extraction from the source is
required. Keep old snapshots' original identities and use a fresh output root.

Publish the regenerated artifact and matching runtime together, then update the
lakehouse's package pin and run its Parquet integration and target-validation
checks. The lakehouse already consumes package 0.4.0/projection 1.2.0 after
[PR #340](https://github.com/microbiomedata/nmdc-lakehouse/pull/340); it must adopt
the next package release to use this change. Its target-version guard prevents
validating 1.2.0 data as 1.3.0 data.

Source-version compatibility is independent: production was last verified on
2026-09-22 as Runtime 2.21.0/schema 11.23.0. The
[source rollout gate](https://github.com/microbiomedata/nmdc-lakehouse/issues/347)
still applies before a complete export against 11.24.0.
