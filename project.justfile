## Add your own just recipes here. This is imported by the main justfile.

# Overriding recipes from the root justfile by adding a recipe with the same
# name in this file is not possible until a known issue in just is fixed,
# https://github.com/casey/just/issues/2540

# ============== Flattened-schema generation ==============

# Generate the flattened LinkML schema (one class per nmdc-schema Database slot).
# Output: ./local/nmdc_schema_flattened.yaml
[group('model development')]
generate-flat-schema:
    @uv run python scripts/generate_flattened_schema.py

# Preview the flattener's output against one record from a local MongoDB.
# Usage: just flatten-preview biosample_set Biosample
[group('model development')]
flatten-preview COLLECTION *ARGS:
    uv run python scripts/flatten_preview.py {{COLLECTION}} {{ARGS}}
