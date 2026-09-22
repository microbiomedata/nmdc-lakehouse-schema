# TextValue and record-type audit

These are historical, read-only production observations from 2026-09-21 using
source schema **11.23.0**. They informed the projection but do not replace its
validation rules. Public evidence and the original acceptance discussion are in
[issue #14](https://github.com/microbiomedata/nmdc-lakehouse-schema/issues/14).
Its original retained-child-table implementation was corrected in
[#17](https://github.com/microbiomedata/nmdc-lakehouse-schema/issues/17) and
[PR #18](https://github.com/microbiomedata/nmdc-lakehouse-schema/pull/18).

## TextValue content

The audit derived paths from Database collections, induced slots, subclasses,
and inlined objects. It read every document in the five applicable collections,
inspected complete TextValue objects including undeclared keys, and expanded
arrays. It was not a sample or a query limited to `has_raw_value`.

| Collection | Documents read | Schema TextValue paths | TextValue objects |
| --- | ---: | ---: | ---: |
| `biosample_set` | 27,352 | 134 | 67,760 |
| `field_research_site_set` | 110 | 4 | 0 |
| `material_processing_set` | 35,234 | 2 | 0 |
| `organism_sample_set` | 0 | 1 | 0 |
| `organism_set` | 0 | 1 | 0 |
| **Total** | **62,696** | **142** | **67,760** |

Every observed TextValue had exactly `has_raw_value` and its expected TextValue
`type` discriminator. All raw values were nonempty strings. No `language` or
unexpected keys were present, even with null/empty values. There were no missing
raw values, malformed scalar wrappers, or empty objects/lists at these paths.

Thus, saying “only `has_raw_value` was populated” would omit the populated
wrapper `type`. What the audit established was that no additional content would
be lost beyond that redundant wrapper discriminator. The runtime still rejects
populated extra content, unexpected discriminators, and non-string raw values.

Of the 142 schema paths, 101 are single-valued and 41 are multivalued. Thirty-one
biosample slots were populated. Ten multivalued slots supplied 3,571 arrays with
one element each in this scan. That observation does not remove schema-declared
multiplicity: the [current projection](textvalue-projection.md) preserves all
occurrences in parent string-array columns.

The scan ran from 21:53:40 to 21:53:49 UTC. Exact cursor counts matched estimated
collection counts before and after scanning. Reads were sequential rather than a
point-in-time snapshot. The other 14 schema collections have no reachable
TextValue-ranged slots and were excluded by schema. Runtime-only collections and
malformed TextValues at undeclared paths were outside scope. Key presence and
population were counted separately; zero, false, and whitespace count as
populated, while null and empty string/list/object values do not.

The source materialized schema SHA-256 was:

```text
ac85605b838789207eba0717dcde2d89c9dc2c312479fcc1cdd469cee8a8fe30
```

The audit script and count-only reports were retained locally as
`audit_textvalues.py`, `report.json`, and `type_report.json` under the dated
`nmdc-textvalue-audit-2026-09-21` audit directory. They are not packaged product
files. No production record values, identifiers, credentials, or connection
strings are included in this documentation or the synthetic test fixtures.

## Polymorphic collections

The source schema declares these four collection ranges with multiple concrete
types. A separate full aggregation from 21:55:40 to 21:55:41 UTC counted their
record types:

| Collection | Declared source class | Concrete types in schema | Types observed | Records |
| --- | --- | ---: | ---: | ---: |
| `configuration_set` | `Configuration` | 2 | 2 | 20 |
| `data_generation_set` | `DataGeneration` | 2 | 2 | 24,676 |
| `material_processing_set` | `MaterialProcessing` | 11 | 8 | 35,234 |
| `workflow_execution_set` | `WorkflowExecution` | 11 | 11 | 34,973 |
| **Total** | | | | **94,903** |

All 94,903 records had an expected type in the collection hierarchy; none had
missing/null or unexpected types. For example, `DataGeneration` contained
`MassSpectrometry` and `NucleotideSequencing`. Configuration records were
`ChromatographyConfiguration` or `MassSpectrometryConfiguration`. Schema classes
can be supported even when no production instances exist: `Culturing`,
`Isolation`, and `MixingProcess` were absent from the material-processing counts.

All 19 source collection ranges require a `type` slot. Its treatment depends on
where the value occurs:

| Location | Projection behavior |
| --- | --- |
| Primary collection record | Keep the original `type` value and use it to select subclass fields. |
| Non-TextValue child-table record | Keep that child record's own `type`. |
| TextValue wrapper | Validate its discriminator, then extract the raw string without a wrapper type column. |
| Single-valued embedded object | Existing expansion uses the type for dispatch but omits that embedded type column. |

The generated primary `type` column remains required data. It does not retain
LinkML's `designates_type: true`: values such as `nmdc:Biosample` identify source
classes, not the generated target class `BiosampleFlat`.

Synthetic checks covered all source subtypes across all 19 collections and
confirmed primary type retention. Generated schemas union subtype columns,
including both supported embedded expansion levels, with subtype-only columns
optional. The generator correction also addresses the nested-dispatch mechanism
reported in [#11](https://github.com/microbiomedata/nmdc-lakehouse-schema/issues/11);
that issue still tracks the separate Agent source-schema upgrade, fixtures,
release, and downstream rollout.
