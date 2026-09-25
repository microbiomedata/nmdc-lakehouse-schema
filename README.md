<a href="https://github.com/linkml/linkml-project-copier"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-teal.json" alt="Copier Badge" style="max-width:100%;"/></a>

# nmdc-lakehouse-schema

The NMDC flattened-schema **product**. It owns the definition of the flat, tabular shape the
NMDC lakehouse writes to Parquet, independent of the data-generation, publication, and
validation code that consumes it:

- **`transforms.schema_generator`** — generates the flat LinkML target schema from a source
  schema (e.g. `nmdc-schema`).
- **`transforms.flatteners`** — the schema-driven flattener that turns supported nested
  LinkML shapes into flat rows. See the support guide for depth limits and known mismatches.
- **`transforms.schema_diff`** — diffs two generated flat schemas so "what changed and why"
  is answerable.

Downstream ETL (the [nmdc-lakehouse](https://github.com/microbiomedata/nmdc-lakehouse) repo)
adopted this package in merged [PR #340](https://github.com/microbiomedata/nmdc-lakehouse/pull/340).
Lakehouse main now uses published package 0.5.0/projection 1.3.0, adopted in
[PR #348](https://github.com/microbiomedata/nmdc-lakehouse/pull/348), with exact
11.23.0 and 11.24.0 source artifacts. See the
[release and adoption checklist](src/docs/schema-workflow.md#release-and-consumer-adoption-checklist)
for future changes.

Projection version `1.3.0` retains the TextValue behavior introduced in `1.2.0`:
raw strings become columns on the
containing record. Single values become strings and repeated values become
string arrays; TextValue-only child tables are removed.
Collection record types remain available for polymorphic dispatch. See the
[TextValue projection contract](src/docs/textvalue-projection.md) for examples,
validation behavior, and migration from earlier artifacts.

## Documentation Website

[https://microbiomedata.github.io/nmdc-lakehouse-schema](https://microbiomedata.github.io/nmdc-lakehouse-schema)

## Development and documentation

- [Schema ownership, versions, Just syntax, and build/deploy workflow](src/docs/schema-workflow.md)
- [TextValue projection and migration](src/docs/textvalue-projection.md)
- [Supported transformations, helper tables, and known data-loss boundaries](src/docs/transformation-support.md)
- [Production TextValue and record-type audit](src/docs/data-audit.md)

From an updated feature checkout:

```sh
just install
just generate-flat-schema
just check-flat-schema
just test
just test-dist
just gen-doc
uv run mkdocs build
```

A merge to `main` rebuilds and deploys documentation from the checked-in schema.
It does not regenerate that canonical artifact or publish a new Python package.
Run `just --list` to see available recipes and `just --dry-run gen-doc` to inspect
resolved documentation commands.

The source input is pinned to tagged `nmdc-schema` release **11.24.0**. With
projection **1.3.0**, the current target is `11.24.0+flat.1.3.0` and has 61 table
classes. See the [upgrade guidance](src/docs/schema-workflow.md#adopting-source-release-11240)
for renamed fields, release verification, and production preflight requirements.
The package also ships a matching 11.23.0 compatibility artifact for production
before migration; see [source version selection](src/docs/source-versions.md).

## Repository structure

| Location | Purpose |
| --- | --- |
| `src/nmdc_lakehouse_schema/transforms/` | Generator, runtime flattener, and schema-diff implementation. |
| `src/nmdc_lakehouse_schema/schema/nmdc_schema_flattened.yaml` | Canonical generated product; regenerate it instead of editing by hand. |
| `src/nmdc_lakehouse_schema/schema/nmdc_lakehouse_schema.yaml` | Remaining Person/PersonCollection template example; removal tracked in [#16](https://github.com/microbiomedata/nmdc-lakehouse-schema/issues/16). |
| `src/nmdc_lakehouse_schema/datamodel/` | Generated models for that template example, not the NMDC flat product. |
| `src/docs/` | Authored documentation; edit these sources. |
| `docs/`, `site/` | Ignored assembled Markdown and built HTML. |
| `tests/` | Projection/artifact regression tests and remaining template fixtures. |
| `project/`, `examples/output/` | Ignored output from template-generation/example recipes. |

## Credits

This project uses the template [linkml-project-copier](https://github.com/linkml/linkml-project-copier).
