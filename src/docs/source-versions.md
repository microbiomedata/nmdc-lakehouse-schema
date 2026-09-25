# Choosing a source release

The canonical product follows the latest deliberately pinned **tagged** NMDC
schema release, currently 11.24.0. Regeneration uses the lockfile; it does not
follow upstream main or discover a newer release automatically.

Production can remain on an older release. Use a generated artifact built from
that exact source package, together with that package's source model. The same
projection rules apply to both supported versions:

| Source package | Packaged flat artifact | Flat version | Tables |
| --- | --- | --- | --- |
| 11.24.0 (canonical) | `schema/nmdc_schema_flattened.yaml` | `11.24.0+flat.1.3.0` | 61 |
| 11.23.0 (compatibility) | `schema/compat/11.23.0/nmdc_schema_flattened.yaml` | `11.23.0+flat.1.3.0` | 60 |

The older model has no DataGeneration credit-association helper. It retains
`principal_investigator` fields and credit `applies_to_person`/PersonValue fields
under their existing names. The 11.24.0 model uses its newer credit/Agent shapes.
Both project TextValues to strings (arrays for repeated values), retain record
types, and preserve nested mobile-phase substances. Selecting a version does
not migrate data between these representations.

## Generate and check

```bash
just generate-flat-schema
just generate-compat-schema
just check-flat-schemas
just test-dist
```

The default environment selects the exact `source-latest` dependency group.
The compatibility recipe selects `source-11-23` and excludes `source-latest`.
Both versions and their dependencies are locked together; uv refuses selecting
both conflicting source groups in one environment. A subsequent ordinary
`uv run` restores the latest default. The compatibility recipe cannot overwrite
the canonical artifact.

CI checks byte-for-byte regeneration and runtime behavior for both versions.
Distribution checks verify that wheels and source archives contain the exact
checked-in bytes of both artifacts. The documentation site continues to show
the canonical artifact; compatibility support does not replace its element pages.

## Consume a matching pair

Consumers select by their installed source package version:

```python
from importlib.metadata import version
from importlib.resources import as_file
from linkml_runtime import SchemaView
from nmdc_lakehouse_schema.artifacts import flat_schema_resource

with as_file(flat_schema_resource(version("nmdc-schema"))) as path:
    target = SchemaView(str(path))
```

Unsupported versions raise an error; there is no nearest-version fallback.
Consumers must also check the artifact's `source_package_version` annotation
against the installed source and verify the actual database migration state
before export. An API's installed package version alone does not establish
that its MongoDB data has been migrated.

Lakehouse selection and that read-only preflight are tracked in
[lakehouse #347](https://github.com/microbiomedata/nmdc-lakehouse/issues/347).
Package 0.5.0 published both artifacts, and
[lakehouse PR #348](https://github.com/microbiomedata/nmdc-lakehouse/pull/348)
adopted that exact release. The 11.23.0 compatibility pair has already produced
an export that passed integrity checks, full target-row validation and staging
checks. The source-to-output preservation audit in lakehouse #347 remains open.
Once production is migrated, select the matching newer
pair and create a fresh snapshot. Existing Parquet files keep their original
source and projection versions.
