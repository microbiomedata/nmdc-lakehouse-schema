## Add your own just recipes here. This is imported by the main justfile.

# Overriding recipes from the root justfile by adding a recipe with the same
# name in this file is not possible until a known issue in just is fixed,
# https://github.com/casey/just/issues/2540

# ============== Flattened-schema generation ==============

# Generate the flattened LinkML schema (one class per nmdc-schema Database slot).
# Output: src/nmdc_lakehouse_schema/schema/nmdc_schema_flattened.yaml
[group('model development')]
generate-flat-schema *ARGS:
    @uv run python scripts/generate_flattened_schema.py {{ARGS}}

# Verify that the published schema and its digest match the pinned source and generator.
[group('model development')]
check-flat-schema:
    @uv run python scripts/generate_flattened_schema.py --check

# Build the explicitly supported production source pair without changing the latest default.
[group('model development')]
generate-compat-schema *ARGS:
    @uv run --no-group source-latest --group source-11-23 python scripts/generate_flattened_schema.py --compatibility {{ARGS}}

# Check every supported artifact using its exact locked source dependency.
[group('model development')]
check-flat-schemas: check-flat-schema
    @just generate-compat-schema --check

# Preview the flattener's output against one record from a local MongoDB.
# Usage: just flatten-preview biosample_set Biosample
[group('model development')]
flatten-preview COLLECTION *ARGS:
    uv run python scripts/flatten_preview.py {{COLLECTION}} {{ARGS}}
