# Schema ownership, versions, and documentation

This repository owns the NMDC flat-schema generator, the runtime flattener,
and the checked-in schema describing their output. The source model comes from
the separate `nmdc-schema` package. The current input is tagged release
**v11.24.0**, with projection **1.3.0**. Upgrades select the latest tagged source
release deliberately and pin it; ordinary regeneration never follows upstream
main or selects a newer release automatically.

A separately packaged 11.23.0 compatibility artifact supports production before
its migration. See [choosing a source release](source-versions.md) for the exact
artifact paths, generation commands, and source/target pairing rules.

## Which repository generates what?

| Component | Responsibility |
| --- | --- |
| `nmdc-schema` | Defines the source classes, slot ranges, inheritance, and cardinalities. |
| `nmdc-lakehouse-schema` | Owns `transforms.schema_generator`, `transforms.flatteners`, `transforms.schema_diff`, and the published flat-schema artifact. Develop new projection rules here. |
| `nmdc-lakehouse` | Reads data, calls the projection engine, writes Parquet, and validates/publishes lakehouse output. |

The intended dependency goes from the lakehouse to this package. The lakehouse
can still call generator functions to construct table definitions at runtime;
that does not make it the owner of the generator implementation. The checked-in
artifact provides the complete, versioned target schema for documentation and
consumers such as target validation.

Lakehouse main consumes published **0.5.0**, adopted in
[PR #348](https://github.com/microbiomedata/nmdc-lakehouse/pull/348).
It supplies projection **1.3.0** and exact artifacts for source 11.23.0 and
11.24.0. [PR #340](https://github.com/microbiomedata/nmdc-lakehouse/pull/340)
removed the consumer's local generator implementation. The consumer selects the
artifact from the installed package; it does not copy or vendor this YAML.
The 11.23.0 pair produced the September snapshot that passed integrity checks,
full target-row validation and BERDL staging. The focused source-to-output
preservation audit remains open in
[lakehouse #347](https://github.com/microbiomedata/nmdc-lakehouse/issues/347).
See the consumer's
[run record](https://github.com/microbiomedata/nmdc-lakehouse/blob/main/docs/runs/2026-09-23-production-staging.md).

Publishing these docs does not publish a Python package, update the lakehouse's
pinned dependency, rewrite MongoDB, or migrate existing snapshots. Adoption of
the parent-column TextValue projection is tracked in
[lakehouse #345](https://github.com/microbiomedata/nmdc-lakehouse/issues/345).
Consumers need matching runtime, target artifact, and source-schema versions.

## The two YAML files

These files are under `src/nmdc_lakehouse_schema/schema/`:

| File | Role |
| --- | --- |
| `nmdc_schema_flattened.yaml` | The canonical generated NMDC product. Source 11.24.0 with projection 1.3.0 has 61 table classes: 19 primary and 42 non-TextValue side tables. Includes version, source provenance, and a content digest. |
| `compat/11.23.0/nmdc_schema_flattened.yaml` | Matching production compatibility artifact: source 11.23.0, projection 1.3.0, 60 classes (19 primary and 41 helpers). Retains the older source fields without migrating records. |
| `nmdc_lakehouse_schema.yaml` | Leftover LinkML project-template example with `NamedThing`, `Person`, `PersonCollection`, and `PersonStatus`. It is not the NMDC source model or an input to the flat-schema generator. |

`scripts/generate_flattened_schema.py` reads the installed
`nmdc_schema/nmdc_materialized_patterns.yaml` and writes the canonical product.
The default `source-latest` dependency group pins `nmdc-schema==11.24.0` in `pyproject.toml` and
`uv.lock`; regeneration does not select the newest upstream schema automatically.

The template's removal is tracked in
[issue #16](https://github.com/microbiomedata/nmdc-lakehouse-schema/issues/16).
Deleting only that YAML would leave these dependencies broken or misleading:

- `gen-project`, `gen-python`, `_test-schema`, and `_test-examples` still select
  it through `LINKML_SCHEMA_NAME` and `source_schema_path`. `just test`, `site`,
  and the existing `deploy` recipe depend on those recipes; CI runs `just test`.
- Generated modules in `src/nmdc_lakehouse_schema/datamodel/` implement the
  Person example. Their initializer re-exports those classes and exposes
  `MAIN_SCHEMA_PATH` pointing to the example YAML.
- `tests/test_data.py`, Person fixtures, and example documentation exercise
  that template model. Retire or replace them alongside the model.
- Package resources/imports may have external consumers. Remove or deprecate
  them deliberately, and inspect the wheel and source distribution.
- Generator configuration, generated-file lint exclusions, README instructions,
  and Copier's `add_example: true` setting need coordinated cleanup.

Do not simply rename `LINKML_SCHEMA_NAME`: it also determines the Python
package/datamodel output directory. The flat-product generator and `just gen-doc`
already have independent inputs and do not need the Person schema. The inspected
lakehouse package-adoption code uses `transforms.*` and the flat product's
resource path, not the example datamodel.

## Regenerate the checked-in schema and local documentation

From a checkout containing the current main branch, with Git, uv, and Just
installed, create a feature branch for changes:

```sh
git switch main
git pull --ff-only
git switch -c update-flat-schema-docs
just install
```

Then run:

```sh
just generate-flat-schema
just generate-compat-schema
just check-flat-schemas
just test
just test-dist
just gen-doc
uv run mkdocs build
```

These commands were exercised for projection 1.3.0 on 2026-09-23. With unchanged
inputs, schema generation reproduces the checked-in bytes. `just check-flat-schema`
checks both reproducibility and the artifact's digest. `just test` also includes
those guards, runtime/generator tests, and the remaining template example tests.
The template Python generator can rewrite its generated timestamp; review that
separately from intended changes.

`just test-dist` builds a wheel and source archive in a temporary directory and
checks regeneration and exact packaged bytes for both supported source artifacts. The same
check gates package publication, before the archives are uploaded to PyPI.

Edit authored documentation under `src/docs/`. Commit source/generator changes,
the regenerated canonical YAML when it changes, and authored docs through a PR.
`docs/` is the assembled, ignored Markdown directory; `site/` is the ignored HTML
build. Do not hand-edit generated element pages or the canonical flat YAML.
Use `uv run mkdocs serve` to preview the assembled docs, or `just testdoc` to
regenerate them and start the server.

`just gen-project` and `just site` still generate the template products described
above. For the NMDC product, use the explicit sequence shown here.

A source-schema upgrade requires changing the pin/lockfile deliberately,
regenerating, and reviewing the resulting shape and compatibility. It is more
than refreshing documentation. Candidate-source checks and automated update PRs
are tracked in [#12](https://github.com/microbiomedata/nmdc-lakehouse-schema/issues/12)
and [#13](https://github.com/microbiomedata/nmdc-lakehouse-schema/issues/13).

## Read the Just recipe if you know Make

```just
gen-doc: _clean-schema-docs _copy-docs _gen-yaml && _add-artifacts
  uv run gen-doc {{gen_doc_args}} -d {{docdir}} {{doc_schema_path}}
```

Running `just gen-doc` performs these steps in order:

1. `_clean-schema-docs` removes the old generated `docs/elements/` directory.
2. `_copy-docs` copies authored files from `src/docs/` into `docs/`.
3. `_gen-yaml` uses LinkML `gen-yaml` to produce the documentation download under
   `docs/schema/` from the checked-in product schema.
4. The indented command runs LinkML's `gen-doc` executable through uv and writes
   the element pages into `docs/elements/`.
5. `_add-artifacts` runs afterward; it is currently an empty extension point.

The header's `&&` introduces **subsequent dependencies**, which execute after
the recipe body. Dependencies before it execute first. It is Just syntax in
that position, not shell syntax. See the
[Just dependency documentation](https://github.com/casey/just#dependencies).

| Make concept | Just equivalent here |
| --- | --- |
| `.PHONY` target | A recipe: commands run without file timestamp comparisons. |
| Prerequisites after `:` | Prior recipe dependencies, run before the body. |
| `$(variable)` | `{{variable}}` expression interpolation. |
| Tab-indented commands | Indented recipe body; spaces are allowed. |
| Helper target naming convention | Leading `_` hides a recipe from normal listings; it is still callable. |

`gen_doc_args` supplies optional generator flags, `docdir` is `docs/elements`, and
`doc_schema_path` is the checked-in flat schema path. `config.public.mk` is loaded
as dotenv-style configuration; it is not included as a Makefile.
`LINKML_DOC_SCHEMA_NAME=nmdc_schema_flattened` selects the documented product.

The executable named `gen-doc` inside `uv run` is a LinkML tool, not a recursive
call to the Just recipe. `just --dry-run gen-doc` displays the resolved commands
without executing them; `just --list` lists the public recipes.

## Where the version numbers come from

There are three separate identities:

| Identity | Source | Example |
| --- | --- | --- |
| Upstream schema version | The loaded `nmdc-schema` schema's `version` | `11.24.0` |
| Projection version | Manually maintained `FLATTENER_VERSION` in `transforms/schema_generator.py` | `1.3.0` |
| Python package version | Git-derived build metadata via `uv-dynamic-versioning` in `pyproject.toml` | A release tag or development version |

`flat_schema_version()` combines the first two:

```text
<source schema version>+flat.<FLATTENER_VERSION>
11.24.0+flat.1.3.0
```

Just and the generator do not increment the projection version automatically.
The convention recorded beside the constant is to increment the minor component
when tables, attributes, or ranges change, and the patch component when only
descriptions or annotations change. This is the project's projection-identity
convention, not a promise that every minor update is backward compatible. A source
version update changes the first component; it does not by itself require changing
`FLATTENER_VERSION` when the projection rules are unchanged.

| Projection | Change |
| --- | --- |
| `1.0.2` | Baseline before the TextValue changes. |
| `1.1.0` | [PR #15](https://github.com/microbiomedata/nmdc-lakehouse-schema/pull/15) extracted raw strings, but still kept repeated TextValues in child tables. |
| `1.2.0` | [PR #18](https://github.com/microbiomedata/nmdc-lakehouse-schema/pull/18) corrected that representation: parent string-array columns replace all 41 TextValue-only child tables. |
| `1.3.0` | [Mobile-phase substances](mobile-phase-substances.md) adds two nested helpers and explicit phase/substance occurrence positions. |

The earlier child-table implementation did not satisfy the intended parent-column
projection. The [TextValue contract](textvalue-projection.md) describes the final
shape and migration requirements.

The canonical artifact also has `flat_schema_sha256`, calculated over its rendered
text with the digest replaced by the generator's 64-zero placeholder. Regeneration
updates it; it is not another manually assigned version. Use the canonical
repository/package artifact for byte-level digest checks. The website's
`schema/` download is a LinkML-expanded rendering produced by `gen-yaml`, so it
is not the same byte stream even though it carries the source annotations.

## Adopting source release 11.24.0

The source upgrade initially shipped in package 0.4.0 as
`11.24.0+flat.1.2.0` (59 tables). That is the superseded artifact baseline;
the canonical artifact here is `11.24.0+flat.1.3.0` (61 tables), which adds the
two nested substance helpers. Independently of that projection update, moving
the source from 11.23.0 to 11.24.0:

- adds `data_generation_set_has_credit_associations` (60 to 61 tables under projection 1.3.0);
- replaces `applies_to_person_*` with `applies_to_agent_*` on study credit rows,
  including Person email/ORCID and Organization ROR columns;
- removes `principal_investigator_*` from Study and DataGeneration; and
- removes `collection_date_inc` from Biosample.

The installed release package supplies the input YAML. The corresponding Git tag's
checked-in materialized file contains a placeholder `0.0.0` version, so downloading
that file alone is not equivalent to using the release wheel.

Regression tests exercise Person and Organization credits under Study and both
DataGeneration subtypes, verify row-key coverage, and preserve collection and
credit-association types. Consumer-side tests must also verify Parquet round trips
and target validation. The [earlier production audit](data-audit.md) used 11.23.0;
it does not establish that production has adopted the renamed 11.24.0 fields.

Before the first 11.24.0 export, audit populated removed/renamed source paths and
the [unsupported nested paths](transformation-support.md). Resolve populated
incompatibilities before treating the output as complete; changing the schema pin
does not migrate MongoDB. The coordinated rollout is tracked in
[schema #11](https://github.com/microbiomedata/nmdc-lakehouse-schema/issues/11) and
[lakehouse #345](https://github.com/microbiomedata/nmdc-lakehouse/issues/345).

This source/projection pair is already published in 0.5.0 and adopted by the
lakehouse. Production's source version remains a separate choice: installing
11.24.0 does not migrate the database, and the retained September candidate uses
11.23.0. A future upgrade follows the release sequence below.

## Release and consumer adoption checklist

1. In a schema-repository branch, pin the intended tagged `nmdc-schema` release
   in the source dependency group and update `uv.lock`. Ordinary regeneration
   continues to use that pin. Update the supported-source selector/tests when
   adding or retiring a source pair. Keep a still-needed production pair.
2. Develop projection changes in this package. Change `FLATTENER_VERSION` when
   the projection contract changes, then regenerate both supported artifacts.
   Run `just check-flat-schemas`, `just test`, `just test-dist`, `just gen-doc`
   and `uv run mkdocs build`. Review the checked-in YAML and authored docs in
   the PR; generated site output is not an input to the package.
3. Merge through human review. Main deploys documentation, but does not publish
   a package. For documentation-only changes with unchanged artifacts/engine,
   no new package is needed for an already-supported consumer.
4. A release maintainer selects an unused package version and publishes a
   matching `vX.Y.Z` Git tag and GitHub Release from the reviewed merged commit.
   The published-release event explicitly triggers `pypi-publish.yaml`; relying
   only on a tag requires that it match the workflow's tag filters. Git-derived
   build metadata supplies the package version; do not hand-edit `_version.py`.
5. Require the build/distribution checks and PyPI publication to succeed. They
   verify both source artifacts against their locked inputs and check exact
   wheel/source-archive contents. The `pypi-release` GitHub environment and PyPI
   trusted publisher must be configured; follow any environment approval rules.
   The operator needs repository release permission, not a PyPI token in a
   local `.env`. Public package installation itself needs no release credential.
6. Verify the published release's version and artifacts. In a separate
   `nmdc-lakehouse` PR, pin that exact package version and regenerate its lockfile.
   For a new source release, update its source extras/selector and tests too.
   Require source/target alignment, synthetic Parquet round trips and target
   validation for every supported pair, plus full checks and distribution tests.
7. After consumer merge, install the matching source pair on the client and pod.
   Use the production preflight before a new export. No consumer-side schema
   generation, YAML copy, package vendoring or MongoDB migration is implied.

For a maintainer who has chosen the version and exact reviewed commit, the
release operation can use the GitHub CLI. Set these variables explicitly and
review the release notes first; this is a publication step, not a local build:

```bash
gh release create "$SCHEMA_TAG" \
  --repo microbiomedata/nmdc-lakehouse-schema \
  --target "$REVIEWED_COMMIT" \
  --title "$SCHEMA_TAG" --notes-file local/release-notes.md
gh run list --repo microbiomedata/nmdc-lakehouse-schema --workflow pypi-publish.yaml
```

`SCHEMA_TAG` is the new `vX.Y.Z` package tag and `REVIEWED_COMMIT` is the full
merged Git commit. Do not reuse or move an existing release tag to publish
changed bytes. The consumer has its own package version and release policy;
using its reviewed checkout does not require an exporter PyPI release.

The two calculated provenance tables are a different contract. Their authored
LinkML YAML is `src/nmdc_lakehouse/schemas/provenance.yaml` in the **consumer**,
not this generated collection schema. That consumer schema drives their Arrow
columns and target validation. See
[local provenance](https://github.com/microbiomedata/nmdc-lakehouse/blob/main/docs/local-provenance.md)
for generation and parent-snapshot binding.

## What a merge publishes

A push to `main`, including a merged PR, triggers
[Deploy docs](https://github.com/microbiomedata/nmdc-lakehouse-schema/blob/main/.github/workflows/deploy-docs.yaml).
It installs dependencies, runs `just gen-doc`, and runs
`uv run mkdocs gh-deploy --force` to commit the site to `gh-pages`. GitHub Pages
then performs its separate **pages build and deployment** step. Both stages must
finish before the live site reflects the merge.

The workflow reads the **checked-in** flat YAML. It does not run
`just generate-flat-schema`, commit a new schema, or repair a stale artifact.
The Build and test workflow checks schema reproducibility. A schema change must
therefore include its regenerated artifact in the PR before merging.

Same-repository PRs get documentation previews from
`test_pages_build.yaml`. The main site is published from `gh-pages`, not directly
from `src/docs/`. Package publication is a separate workflow triggered by a
matching version-tag push or a published GitHub Release; merging to main alone
does not publish a package.

To deliberately rebuild the main site without a new commit, use GitHub Actions'
**Run workflow** button for Deploy docs, or this equivalent manual command:

```sh
gh workflow run deploy-docs.yaml \
  --repo microbiomedata/nmdc-lakehouse-schema --ref main
```

To inspect deployment progress:

```sh
gh run list --repo microbiomedata/nmdc-lakehouse-schema --limit 10
```

If the site appears stale, compare its content with the merged schema, check both
deployment stages, and then refresh the browser. A rendered name is not evidence
of an old build: LinkML documentation can display snake_case class keys in
CamelCase. In projection 1.1.0, `BiosampleSetHostDiet` represented the YAML class
`biosample_set_host_diet`; in 1.2.0, neither class/page should exist. Find
`host_diet` in `BiosampleFlat` instead. Clearing generated element pages before
regeneration prevents deleted classes from lingering after local rebuilds.

## Generator history

The original lakehouse generator history includes Mark Andrew Miller's initial
[implementation](https://github.com/microbiomedata/nmdc-lakehouse/commit/f98a4fd)
and subsequent schema/type/version changes. Sierra Taylor Moxon introduced and
updated the schema-repository copy in commits
[35da2bb](https://github.com/microbiomedata/nmdc-lakehouse-schema/commit/35da2bb),
[7667a14](https://github.com/microbiomedata/nmdc-lakehouse-schema/commit/7667a14),
[f877d85](https://github.com/microbiomedata/nmdc-lakehouse-schema/commit/f877d85), and
[4fd595a](https://github.com/microbiomedata/nmdc-lakehouse-schema/commit/4fd595a).

A comparison before the TextValue work used lakehouse `8911299` and schema
repository `e117d62`, both against source schema 11.23.0. Both generated 99 classes
and 2,258 attributes with identical class names and attribute definitions. They
were not byte-identical: projection versions, generator identity, and producer
mapping metadata differed. The schema repository keeps schema structure separate
from per-write ETL producer identity. The TextValue and embedded-polymorphism
changes subsequently made here intentionally change the engine relative to the
legacy lakehouse copy; do not assume the two generators still match.
