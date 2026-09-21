# TextValue projection

Projection version `1.1.0` maps a slot whose declared range is exactly
`TextValue` to its `has_raw_value` string. It uses the source schema to identify
these slots. Other classes that contain `has_raw_value`, including
QuantityValue, TimestampValue, PersonValue, and ControlledIdentifiedTermValue,
keep their existing projection rules.

For a single-valued slot, the column keeps the slot's name. This synthetic input:

```yaml
id: synthetic:sample
type: nmdc:Biosample
geo_loc_name:
  type: nmdc:TextValue
  has_raw_value: example location
```

produces these flat values:

```yaml
id: synthetic:sample
type: nmdc:Biosample
geo_loc_name: example location
```

The generated column has range `string`, the source slot's description, an
extraction note, and applicable requiredness. Subclass-only columns remain
optional in a table combining a class hierarchy. A TextValue inside another
inlined object retains the enclosing path prefix: `detail.label.has_raw_value`
becomes `detail_label`. The rule also applies inside child-table records and at
the existing second expansion level.

## Repeated values

A multivalued TextValue slot keeps its existing child table named
`<collection>_<slot>`. Each occurrence produces one row with `parent_id` and a
string column named after the slot. For example, two `host_diet` TextValues
produce two rows in `biosample_set_host_diet`, with columns `parent_id` and
`host_diet`. Duplicates remain separate rows. Values are never joined with a
delimiter or reduced to the first item. Row order is not a relational contract.

An absent, null, or empty-list multivalued slot produces no rows. A TextValue
occurrence with a missing/null raw value produces a row with its parent ID and
a null value column, preserving occurrence count. A single object supplied to
a multivalued slot is treated as one occurrence, consistent with the existing
flattener.

Schema 11.23.0 has 101 single-valued and 41 multivalued TextValue paths across
its collection classes and their subclasses. None are nested multivalued
TextValue slots. Such a nested repeated slot requires a separate child-table
mapping: both schema generation and row projection reject that unsupported
shape instead of silently dropping its values.

## Nulls, extra fields, and types

For single-valued TextValues, absent objects and missing/null `has_raw_value`
fields omit the output key; schema-directed writers represent it as null.
Empty strings, whitespace, Unicode, delimiters, and newlines are preserved
exactly. A populated raw value must already be a string; the flattener does
not stringify numbers, lists, objects, or malformed scalar TextValues.

The wrapper may omit `type` or contain a null/empty type, `TextValue`,
`nmdc:TextValue`, or `https://w3id.org/nmdc/TextValue`. These discriminators
identify the wrapper whose raw string is extracted, so they are omitted from
its projection. A different discriminator is rejected.

Populated extra fields, including `language` and unknown keys, are rejected
with a `ValueError`. Diagnostics contain no source values or arbitrary field
names. Extra fields with null, empty string, empty list, or empty object values
are allowed; zero, false, and whitespace count as populated. A production audit
on 2026-09-21 found 67,760 TextValues with only the raw string and type populated;
this check prevents silently losing content if that observation changes.

Collection records retain their original `type` column and use it to select
subclass fields. Non-TextValue child records also retain their own type.
The existing omission of types for single-valued embedded objects is unchanged.
Generated columns preserve the type value without marking it as the generated
class's LinkML type designator.

## Migrating consumers

The generated artifact version changes from `11.23.0+flat.1.0.2` to
`11.23.0+flat.1.1.0`. This is a change to column names and shape:

| Location | Earlier columns | New columns |
| --- | --- | --- |
| Single TextValue slot `s` | `s_has_raw_value`, `s_language` | `s` |
| Repeated TextValue child table | `parent_id`, `has_raw_value`, `language`, `type` | `parent_id`, `s` |
| Nested single TextValue `p.s` | `p_s_has_raw_value`, `p_s_language` | `p_s` |

Table names and parent relationships remain unchanged. Update queries and
metadata references to the renamed columns. Existing snapshots retain their
original schema versions; do not relabel them as the new projection.

Adopt the generator, row flattener, and published schema from the same package
release with the matching pinned `nmdc-schema` version. The current lakehouse
main branch still has a legacy implementation; its migration to this package
is tracked in [PR #340](https://github.com/microbiomedata/nmdc-lakehouse/pull/340).
Installing only a new artifact beside the legacy runtime would make the
declared schema disagree with the rows it writes.

Regenerate and verify the artifact in this repository:

```sh
just generate-flat-schema
just check-flat-schema
just test
```

The generator writes
`src/nmdc_lakehouse_schema/schema/nmdc_schema_flattened.yaml` and calculates its
content digest. Both the source distribution and wheel must ship those same
bytes. The package release version is separate from the projection version.
