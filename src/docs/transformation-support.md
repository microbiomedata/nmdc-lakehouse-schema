# Supported transformations and boundaries

The projection supports a fixed set of shapes. It is not a general recursive
normalizer, and it has no automatic JSON fallback for shapes it cannot flatten.
Some unsupported populated paths are silently omitted. The TextValue validation
rules are stricter than the general flattener's behavior.

This describes schema-repository projection **1.2.0**, source schema **11.23.0**,
and the lakehouse Parquet writer inspected on 2026-09-22. The lakehouse's adoption
of this projection is still pending; see the [workflow guide](schema-workflow.md).
These findings combine code inspection, synthetic runtime/schema comparisons,
and an inventory of the pinned source schema. They are not a production-data
coverage audit.

## What becomes a column or helper table?

Here, "flat" allows native arrays of scalar values. It does not mean every cell
contains exactly one scalar, as in a strictly normalized relational design.

| Source shape | Current representation | Helper table? |
| --- | --- | --- |
| Scalar or enum | One column, retaining the declared LinkML range. The sink maps supported numeric/boolean types to Arrow types and enums to strings. | No |
| Repeated scalar or enum | Native scalar array in the containing row; a singleton input is wrapped as a list. | No |
| Exact `TextValue` range, single or repeated | Extract `has_raw_value` into a string or string array on the containing row. Applies at paths the expansion actually visits. | No |
| Single reference to an identified class, on the collection record | Identifier string column. | No |
| Repeated references, on the collection record | Identifier array plus a junction table with `parent_id` and one referenced identifier per row. | Yes, emitted in addition to the array |
| Single embedded wrapper with scalar, enum, or TextValue members | Prefixed columns such as `depth_has_numeric_value`, `depth_has_unit`, or `detail_label`. Repeated scalar/TextValue members remain arrays. | No |
| Single embedded wrapper containing a second single embedded object | Another prefix level, such as `env_broad_scale_term_id` and `env_broad_scale_term_name`. | No, within the depth limit |
| Repeated embedded non-TextValue objects, directly on the collection record | One child row per object, with `parent_id` and the child's supported flattened fields. | Yes |
| Inheritance and class-based polymorphism | Induced inherited slots plus optional columns for subclass fields; runtime selects a known class using `type`. | Follows the slot rules above |

The only wrapper-specific scalar extraction is for a slot whose range is exactly
`TextValue`. A class with a similar name, a TextValue subclass used as the declared
range, or another class containing `has_raw_value` does not receive that special
rule. QuantityValue, PersonValue, TimestampValue, GeolocationValue, and controlled
term wrappers use the general embedded-object rules.

Whether a class is embedded is determined by explicit `inlined` when present;
otherwise, a class with an identifier is treated as a reference and a class
without one as embedded. Nested controlled-term expansion also accepts embedded
term objects even where their class has an identifier. This is not a general
normalization of every possible LinkML reference representation.

Primary records and non-TextValue child rows retain their own `type`. Types of
single embedded objects are used for dispatch but are omitted from the columns.
See the [type audit](data-audit.md#polymorphic-collections) for the four
polymorphic collections in the pinned schema.

## When helper tables are required

To represent several objects with several attributes while keeping columns
scalar or arrays of scalars, this implementation uses child tables. For example,
repeated `chem_administration` objects become rows in
`biosample_set_chem_administration`, each linked to the biosample by `parent_id`.
Each child can retain scalar arrays, projected TextValues, and supported single
embedded objects.

For repeated identifier references, the helper is a query convenience: the
primary array already carries the identifiers. For repeated TextValues or
primitive values, an array is sufficient and no helper is generated.

Important limits of the current child-table representation:

- Helpers are discovered only among collection-root slots, including inherited
  and subclass slots. The generator and runtime do not recursively create
  grandchild helpers.
- Emission requires a truthy root field named `id`; an alternative LinkML
  identifier name is not substituted automatically.
- Rows carry the root `parent_id`. The flattener does not synthesize a child
  occurrence identifier or list-position column. File row order is not an
  explicit ordering contract for SQL queries.
- Missing, null, and empty child lists all yield no child rows. Non-object
  elements in an embedded child list are skipped. This is not a lossless
  round-trip representation of all input distinctions.

There is no fundamental relational limit preventing nested repeated wrappers
from being normalized. Supporting them would require recursive child tables,
keys identifying each intermediate occurrence, and explicit positions where
order matters. Those transformations are not currently implemented.

## Unsupported shapes and known mismatches

### Repeated classes inside embedded objects

An embedded object's repeated **non-TextValue class** member is skipped. It does
not matter whether the containing object came from a single-valued root slot or
is already a child-table row. No grandchild table or JSON column captures it.
Repeated references nested there are also not reliably retained: child-schema
generation can declare an identifier array that runtime expansion never fills.

This is already a shape allowed by source schema 11.23.0:

```text
configuration_set
  ChromatographyConfiguration
    ordered_mobile_phases[*]       MobilePhaseSegment -> child table
      substances_used[*]           PortionOfSubstance -> omitted

material_processing_set
  ChromatographicSeparationProcess
    ordered_mobile_phases[*]       MobilePhaseSegment -> child table
      substances_used[*]           PortionOfSubstance -> omitted
```

For example, this minimal synthetic projection input:

```yaml
id: example:configuration
type: nmdc:ChromatographyConfiguration
ordered_mobile_phases:
  - type: nmdc:MobilePhaseSegment
    duration:
      has_numeric_value: 5.0
      has_unit: min
    substances_used:
      - type: nmdc:PortionOfSubstance
        known_as: water
```

produces this child row in `configuration_set_ordered_mobile_phases`:

```yaml
parent_id: example:configuration
type: nmdc:MobilePhaseSegment
duration_has_numeric_value: 5.0
duration_has_unit: min
```

`substances_used` is absent from both the generated helper schema and runtime
row. There is no `configuration_set_ordered_mobile_phases_substances_used`
helper. This synthetic example tests projection behavior; it is not a complete
source-schema validation fixture or a production record.

The source-shape inspection also found `organism_set.classified_as[*].relations[*]`
and deeper `term.relations[*]` paths in controlled-term wrappers. Twenty distinct
collection-relative paths reached a repeated-class/depth boundary in this
inspection: the two mobile-phase paths, `classified_as.relations`, and 17
controlled-term relation paths. This is a bounded structural inventory, not a
claim that all possible unsupported representations have been enumerated.
Whether these paths contain production data still needs a separate audit; the
earlier TextValue/type audit did not inspect them.

### Depth limits and schema/runtime disagreement

For primary rows, generic expansion supports a scalar leaf after at most two
single-object edges:

```text
record.wrapper.scalar                  -> wrapper_scalar
record.wrapper.inner.scalar            -> wrapper_inner_scalar
record.wrapper.inner.deeper.scalar     -> omitted
```

TextValue extraction is special at each visited slot, so a visited TextValue's
`has_raw_value` is extracted without another generic expansion step. An object
hidden beneath an unsupported enclosing path is never visited, however, even
if it contains TextValues.

There is also a confirmed synthetic mismatch for child tables. Their schema is
generated with `flatten_class_def(child_class)`, while their row uses
`_expand_inlined(child)`. For `child.middle.leaf.label`, the schema can declare
`middle_leaf_label`, but runtime skips the value. A schema-directed writer then
fills that declared column with null; optional empty-column pruning may remove
it. Child runtime supports `child.middle.label`, one fewer generic embedded
object edge than the child schema can describe. The same mismatch can affect a
TextValue under that skipped `leaf` object.

### Other shapes without a dedicated transformation

- Arbitrary dictionaries, keyed object collections, lists of lists, and
  heterogeneous object/scalar unions have no dedicated normalization rule.
  The decision tree reads the induced slot's `range`, cardinality, and inlining;
  it does not implement general `any_of`/`all_of` shape transformations.
- Unknown populated input keys are ignored. A non-dictionary value where a
  single embedded object is expected is skipped. General projection is not
  full source-instance validation.
- Nested reference slots are not handled uniformly with root references.
  A root identifier string is retained; a nested identifier string can be
  skipped where the expansion expects an embedded dictionary instead.
- Polymorphism uses class inheritance, not arbitrary unions. Conflicting flat
  column definitions keep the first definition, with the base class taking
  precedence. There is no union-type reconciliation. Runtime primary dispatch
  also accepts known classes outside the declared hierarchy, whereas side-table
  dispatch constrains them; this is an existing guardrail gap.

Silent-loss detection and dispatch checks are tracked in
[lakehouse #129](https://github.com/microbiomedata/nmdc-lakehouse/issues/129).
The earlier [#62](https://github.com/microbiomedata/nmdc-lakehouse/issues/62) is
closed, but the repeated-class limitation is reproducible in projection 1.2.0.
Its historical statement that only scalar recursive shapes were known must not
be used as evidence that today's pinned schema has no such class-valued paths.

## Can embedded JSON nevertheless appear in a table?

The normal schema-directed writer creates scalar and scalar-array fields. It
does not preserve an unsupported subtree as JSON or an Arrow struct. The main
failure mode above is omission, not a JSON fallback.

There are two separate mechanisms to distinguish from that behavior:

1. If a dictionary reaches a declared **string** field through a scalar or
   reference path, the lakehouse sink's permissive `_coerce` calls `str(value)`.
   A synthetic `{"nested": true}` value therefore becomes the string
   `{'nested': True}`. That is Python dictionary text, not valid JSON. The same
   coercion applies to elements of string arrays. Numeric/boolean fields can
   instead fail Arrow conversion. Validated TextValue extraction rejects such
   malformed raw values before the writer.
2. The sink can be called without a schema. That separate mode uses
   `pyarrow.Table.from_pylist` and can infer nested Arrow structs/lists. It is not
   a fallback selected by the collection flattener when nesting is too deep.

The JSON stored in the Parquet footer for Spark describes the **table schema**;
it does not contain unsupported source objects.

The implementation evidence is in
[`flatteners.py`](https://github.com/microbiomedata/nmdc-lakehouse-schema/blob/2c2c637a78b1a40ce97b96e616f12b6c20db7049/src/nmdc_lakehouse_schema/transforms/flatteners.py),
[`schema_generator.py`](https://github.com/microbiomedata/nmdc-lakehouse-schema/blob/2c2c637a78b1a40ce97b96e616f12b6c20db7049/src/nmdc_lakehouse_schema/transforms/schema_generator.py),
and the lakehouse
[`parquet_sink.py`](https://github.com/microbiomedata/nmdc-lakehouse/blob/cc5a9c0f95359f621c2752dbcd52bb98994373db/src/nmdc_lakehouse/sinks/parquet_sink.py).
