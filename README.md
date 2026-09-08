<a href="https://github.com/linkml/linkml-project-copier"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border-teal.json" alt="Copier Badge" style="max-width:100%;"/></a>

# nmdc-lakehouse-schema

The NMDC flattened-schema **product**. It owns the definition of the flat, tabular shape the
NMDC lakehouse writes to Parquet, independent of the data-generation, publication, and
validation code that consumes it:

- **`transforms.schema_generator`** — generates the flat LinkML target schema from a source
  schema (e.g. `nmdc-schema`).
- **`transforms.flatteners`** — the schema-driven flattener that turns nested LinkML records
  into flat rows, mirroring the generator's decision tree one-to-one.
- **`transforms.schema_diff`** — diffs two generated flat schemas so "what changed and why"
  is answerable.

Downstream ETL (the [nmdc-lakehouse](https://github.com/microbiomedata/nmdc-lakehouse) repo)
depends on this package rather than defining the engine itself.

## Documentation Website

[https://microbiomedata.github.io/nmdc-lakehouse-schema](https://microbiomedata.github.io/nmdc-lakehouse-schema)

## Repository Structure

* [docs/](docs/) - mkdocs-managed documentation
  * [elements/](docs/elements/) - generated schema documentation
* [examples/](examples/) - Examples of using the schema
* [project/](project/) - project files (these files are auto-generated, do not edit)
* [src/](src/) - source files (edit these)
  * [nmdc_lakehouse_schema](src/nmdc_lakehouse_schema)
    * [schema/](src/nmdc_lakehouse_schema/schema) -- LinkML schema
      (edit this)
    * [datamodel/](src/nmdc_lakehouse_schema/datamodel) -- generated
      Python datamodel
* [tests/](tests/) - Python tests
  * [data/](tests/data) - Example data

## Developer Tools

There are several pre-defined command-recipes available.
They are written for the command runner [just](https://github.com/casey/just/).
To list all pre-defined commands, run `just` or `just --list`.

## Credits

This project uses the template [linkml-project-copier](https://github.com/linkml/linkml-project-copier).
