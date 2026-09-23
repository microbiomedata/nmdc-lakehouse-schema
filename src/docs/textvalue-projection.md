# TextValue projection

Projection version `1.2.0` maps slots whose declared range is exactly
`TextValue` to a string slot on its containing record. Single-valued source slots
become scalar strings; multivalued source slots become string arrays. TextValue
slots never create a separate class or child table.

This rule applies at paths the flattener visits. It does not overcome unsupported
enclosing structures or general depth limits; the
[transformation support guide](transformation-support.md) documents those limits
and a known child-schema/runtime depth mismatch.

The source schema identifies these slots. Other classes that contain
`has_raw_value`, including QuantityValue, TimestampValue, PersonValue, and
ControlledIdentifiedTermValue, keep their existing projection rules.

For repository ownership, the two YAML files, version numbering, and build/deploy
commands, see the [workflow guide](schema-workflow.md). The dated
[audit report](data-audit.md) records the MongoDB evidence and polymorphic
collection inventory.

## Parent columns

This synthetic input:

```yaml
id: synthetic:sample
type: nmdc:Biosample
geo_loc_name:
  type: nmdc:TextValue
  has_raw_value: example location
host_diet:
  - type: nmdc:TextValue
    has_raw_value: herbivore
  - type: nmdc:TextValue
    has_raw_value: high-fiber
```

produces one row in `biosample_set`:

```yaml
id: synthetic:sample
type: nmdc:Biosample
geo_loc_name: example location
host_diet:
  - herbivore
  - high-fiber
```

The generated `BiosampleFlat` class declares `geo_loc_name` with `range: string`
and `multivalued: false`, and `host_diet` with `range: string` and
`multivalued: true`. The latter becomes a Parquet ARRAY of strings, following the
existing rule for multivalued scalar slots. There is no `biosample_set_host_diet`
class, table, or emitted side-table row. The relevant generated schema structure is:

```yaml
classes:
  BiosampleFlat:
    attributes:
      host_diet:
        range: string
        multivalued: true
```

Columns keep the source slot's name, description, and applicable requiredness,
plus an extraction note. A TextValue inside another inlined object retains the
enclosing path prefix: `detail.label.has_raw_value` becomes `detail_label`.
The same rule applies to repeated TextValues at both supported expansion levels
and to TextValues inside non-TextValue child-table records.

At both expansion levels, generated columns include the embedded class and its
descendants, matching runtime dispatch on the embedded object's `type`. Columns
contributed only by a subtype are optional and identify that subtype in their
descriptions. Base-class column definitions take precedence.

Schemas 11.23.0 and 11.24.0 have 101 single-valued and 41 multivalued TextValue paths
across their collection classes and subclasses. All 142 belong to their parent
classes. Under projection 1.2.0, removing the 41 TextValue-only tables left 58 table
classes with source 11.23.0 and 59 with source 11.24.0. Projection 1.3.0 retains
this TextValue contract and adds two nested substance helpers: the canonical
11.24.0 product now has 61 classes (19 primary and 42 non-TextValue helpers).

## Multiplicity, nulls, and empty values

Repeated values preserve their order and every occurrence, including duplicates.
Values are never joined with a delimiter or reduced to the first item. A single
object supplied to a multivalued slot becomes a one-element array, consistent
with the existing scalar flattener.

An absent or null TextValue slot omits the output key; schema-directed writers
represent it as null. An empty multivalued list remains `[]`. A missing/null raw
value in a repeated occurrence becomes a null array element, preserving its
position and the occurrence count. A missing/null raw value in a single-valued
TextValue omits the output key.

Empty strings, whitespace, Unicode, delimiters, and newlines are preserved
exactly. A populated raw value must already be a string; the flattener does
not stringify numbers, lists, objects, or malformed scalar TextValues.

## Extra fields and types

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

The generated artifact version changes from `11.23.0+flat.1.1.0` to
`11.23.0+flat.1.2.0`. Version 1.1.0 extracted raw strings but retained repeated
TextValues in child tables. Version 1.2.0 moves those values into parent columns
and removes the corresponding child-table classes and runtime rows.

| Source slot | Projection 1.0.2 | Projection 1.1.0 | Projection 1.2.0 |
| --- | --- | --- | --- |
| Single TextValue `s` | Parent `s_has_raw_value`, `s_language` | Parent string `s` | Parent string `s` |
| Repeated TextValue `s` | Child `parent_id`, `has_raw_value`, `language`, `type` | Child `parent_id`, `s` | Parent string array `s`; no TextValue child table |
| Nested single TextValue `p.s` | Parent `p_s_has_raw_value`, `p_s_language` | Parent string `p_s` | Parent string `p_s` |

Update queries and metadata that refer to the removed child tables. Existing
snapshots retain their original schema versions and table layouts; do not relabel
them as the new projection. When creating a new snapshot, do not carry obsolete
TextValue-only table files forward from an earlier snapshot.

Adopt the generator, row flattener, and published schema from the same package
release with the matching pinned `nmdc-schema` version. Lakehouse main adopted
package 0.4.0/projection 1.2.0 in merged
[PR #340](https://github.com/microbiomedata/nmdc-lakehouse/pull/340); projection 1.3.0
requires a new package release and consumer update. Runtime and artifact must
remain from the same package. Compatibility with downstream
catalogs that reject arrays is tracked separately in
[lakehouse #342](https://github.com/microbiomedata/nmdc-lakehouse/issues/342).

Regenerate and verify the artifact and documentation in this repository:

```sh
just generate-flat-schema
just check-flat-schema
just test
just gen-doc
uv run mkdocs build
```

The generator writes
`src/nmdc_lakehouse_schema/schema/nmdc_schema_flattened.yaml` and calculates its
content digest. Both the source distribution and wheel must ship those same
bytes. The package release version is separate from the projection version.
Documentation generation removes old generated element pages before rebuilding,
so removed classes do not remain browsable after a local rebuild.
