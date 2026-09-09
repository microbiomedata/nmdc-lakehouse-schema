"""Transform layer.

Flattens the nested NMDC / LinkML object model into a tabular representation
suitable for Parquet / Iceberg. The LinkML ``SchemaView`` is used to drive
the flattening so that the shape of the output follows the schema.

This package is the product consumed by downstream ETL (e.g. nmdc-lakehouse):
the runtime flattener, the generator that describes the flat shape as a LinkML
schema, and the tool that diffs two generated schemas. The names re-exported
here are the supported public API.
"""

from nmdc_lakehouse_schema.transforms.flatteners import (
    SchemaDrivenFlattener,
    flatten_record,
    side_table_rows,
)
from nmdc_lakehouse_schema.transforms.schema_diff import (
    SchemaDiffError,
    diff_schemas,
    render_diff,
)
from nmdc_lakehouse_schema.transforms.schema_generator import (
    flatten_class_def,
    flatten_database_schema,
    side_table_class_defs,
)

__all__ = [
    "SchemaDrivenFlattener",
    "flatten_record",
    "side_table_rows",
    "flatten_class_def",
    "flatten_database_schema",
    "side_table_class_defs",
    "diff_schemas",
    "render_diff",
    "SchemaDiffError",
]
