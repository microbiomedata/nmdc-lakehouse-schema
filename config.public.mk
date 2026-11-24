# config.public.mk

# This file is public in git. No sensitive info allowed.

###### schema definition variables, used by justfile

# Note:
# - just works fine with quoted variables of dot-env files like this one
LINKML_SCHEMA_NAME="nmdc_lakehouse_schema"
LINKML_SCHEMA_AUTHOR="Sierra Moxon <smoxon@lbl.gov>"
LINKML_SCHEMA_DESCRIPTION="This is the project description."
LINKML_SCHEMA_SOURCE_DIR="src/nmdc_lakehouse_schema/schema"

# The product schema: the flattened, tabular target that `just generate-flat-schema`
# writes and the docs site publishes. LINKML_SCHEMA_NAME above is the Python package
# name, not a schema file.
LINKML_DOC_SCHEMA_NAME="nmdc_schema_flattened"

###### linkml generator variables, used by justfile

## pass args if gendoc ignores config.yaml (i.e. --no-mergeimports)
LINKML_GENERATORS_DOC_ARGS=

