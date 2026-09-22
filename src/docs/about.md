# About nmdc-lakehouse-schema

This repository owns the NMDC flattened-schema product: the LinkML generator,
the runtime flattener that produces the declared rows, a schema-diff tool, and
the generated target-schema artifact. The source model is maintained in
[nmdc-schema](https://github.com/microbiomedata/nmdc-schema), and data loading and
publication are handled by
[nmdc-lakehouse](https://github.com/microbiomedata/nmdc-lakehouse).

See the [workflow guide](schema-workflow.md) for repository responsibilities,
generator history, remaining template cleanup, version numbering, and the
current package-adoption boundary. The
[TextValue contract](textvalue-projection.md) describes scalar and repeated string
columns, retained record types, validation, and migration.
The [transformation support guide](transformation-support.md) records which
shapes become columns or helper tables and where populated content can be lost.
