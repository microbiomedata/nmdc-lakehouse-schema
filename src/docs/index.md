# nmdc-lakehouse-schema

The NMDC flat-schema product defines how nested source records become lakehouse
tables. This package contains the schema generator, runtime flattener,
schema comparison tools, and the canonical generated LinkML target schema.

Projection `1.2.0` puts TextValue strings directly on their containing records.
For example, `BiosampleFlat.host_diet` is a multivalued string slot; there is no
`BiosampleSetHostDiet` class or separate TextValue table. With source schema
11.24.0, the product has 59 table classes.

- [Generated schema reference](elements/index.md)
- [TextValue projection and migration](textvalue-projection.md)
- [Supported transformations, helper tables, and known data-loss boundaries](transformation-support.md)
- [Schema ownership, versions, Just recipes, and documentation deployment](schema-workflow.md)
- [Production TextValue and record-type audit](data-audit.md)

The source model is maintained in `nmdc-schema`. The `nmdc-lakehouse` application
consumes the projection to write and validate data; adopting a new package and
migrating existing data are separate from publishing this documentation.
