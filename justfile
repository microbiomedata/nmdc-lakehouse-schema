# ============ Shell configuration for Windows ============

# On Windows the "bash" shell from Git for Windows is used.
# If Git is installed in a non-standard location, edit the path below.
set windows-shell := ["C:/Program Files/Git/bin/bash", "-cu"]

# ============ Variables used in recipes ============

# Detect WSL2 variable
_wsl2_check := `[ -n "${WSL_INTEROP:-}" ] && [ -z "${JUST_TEMPDIR:-}" ] && echo "ERROR" || echo "OK"`

# Load environment variables from config.public.mk or specified file
set dotenv-load := true
# set dotenv-filename := env_var_or_default("LINKML_ENVIRONMENT_FILENAME", "config.public.mk")
set dotenv-filename := x'${LINKML_ENVIRONMENT_FILENAME:-config.public.mk}'

# Set shebang line for cross-platform Python recipes (assumes presence of launcher on Windows)
shebang := if os() == 'windows' {
  'py'
} else {
  '/usr/bin/env python3'
}

# Environment variables with defaults
schema_name := env_var_or_default("LINKML_SCHEMA_NAME", "_no_schema_given_")
source_schema_dir := env_var_or_default("LINKML_SCHEMA_SOURCE_DIR", "")
# Schema documented and published on the docs site. Defaults to schema_name so the
# template behaves unchanged; set LINKML_DOC_SCHEMA_NAME to document a different
# schema (here: the flattened product schema rather than the datamodel boilerplate).
doc_schema_name := env_var_or_default("LINKML_DOC_SCHEMA_NAME", schema_name)
gen_doc_args := env_var_or_default("LINKML_GENERATORS_DOC_ARGS", "")

# Directory variables
doc_schema_path := source_schema_dir / doc_schema_name + ".yaml"
docs_src := "src/docs"  # Authored documentation sources (version controlled)
docs_build := "docs"  # Assembled mkdocs build dir (regenerated, git-ignored)
docdir := docs_build / "elements"  # Directory for generated documentation
distrib_schema_path := docs_build / "schema"  # Directory for publishing schema artifacts

# ============== Project recipes ==============

# List all commands as default command. The prefix "_" hides the command.
_default: _status
    @{{ if _wsl2_check == "ERROR" { "echo 'WSL2 detected: run export JUST_TEMPDIR=/tmp'" } else { "" } }}
    @just --list

# WSL2 status check - warns but does not abort (safe to use in _status/_default)
[private]
_wsl2_status_check:
    @if [ -n "${WSL_INTEROP:-}" ] && [ -z "${JUST_TEMPDIR:-}" ]; then \
      echo "WARNING: WSL2 detected but JUST_TEMPDIR is not set."; \
      echo "Shebang recipes will fail with 'Permission denied' errors."; \
      echo "Fix: run 'export JUST_TEMPDIR=/tmp'"; \
    fi

# WSL2 compatibility check - fails early with helpful message
[private]
_wsl2_compat_check:
    @if [ -n "${WSL_INTEROP:-}" ] && [ -z "${JUST_TEMPDIR:-}" ]; then \
      echo "ERROR: WSL2 detected but JUST_TEMPDIR is not set."; \
      echo "Shebang recipes will fail with 'Permission denied' errors."; \
      echo ""; \
      echo "Fix: run this command:"; \
      echo ""; \
      echo "  export JUST_TEMPDIR=/tmp"; \
      echo ""; \
      echo "Or add it to your ~/.bashrc for persistence."; \
      exit 1; \
    fi

# Initialize a new project (use this for projects not yet under version control)
[group('project management')]
setup: _wsl2_compat_check _check-config _git-init install _git-add && _setup_part2
  git commit -m "Initialise git with minimal project" -a || true

_setup_part2: gen-doc
  @echo
  @echo '=== Setup completed! ==='

# Install project dependencies
[group('project management')]
install:
  uv sync --group dev

# Updates project template and LinkML package
[group('project management')]
update: _update-template _update-linkml

# Clean all generated files
[group('project management')]
clean: _wsl2_compat_check
  rm -rf tmp
  rm -rf {{docs_build}}

# Generate the documentation site locally
[group('model development')]
site: gen-doc

# Deploy documentation site to Github Pages
[group('deployment')]
deploy: site
  mkd-gh-deploy

# Run all tests
[group('model development')]
test: _test-schema _test-python

# Build distributions and verify their canonical schema bytes.
test-dist: check-flat-schemas
  #!/usr/bin/env bash
  set -euo pipefail
  scratch="$(mktemp -d)"
  trap 'rm -rf "$scratch"' EXIT
  uv build --out-dir "$scratch"
  uv run python scripts/check_distribution_schema.py "$scratch"/*.whl "$scratch"/*.tar.gz

# Run linting
[group('model development')]
lint:
  uv run linkml-lint {{source_schema_dir}}

# Generate md documentation for the schema and add artifacts
[group('model development')]
gen-doc: _clean-schema-docs _copy-docs _gen-yaml && _add-artifacts
  uv run gen-doc {{gen_doc_args}} -d {{docdir}} {{doc_schema_path}}

# Remove pages for schema elements that no longer exist before rebuilding.
_clean-schema-docs:
  uv run python -c "from pathlib import Path; import shutil; p = Path('{{docdir}}'); shutil.rmtree(p) if p.exists() else None"

# Assemble the docs build dir from authored sources in src/docs
_copy-docs:
  mkdir -p {{docs_build}}
  cp -R {{docs_src}}/. {{docs_build}}/

# Build docs and run test server
[group('model development')]
testdoc: gen-doc _serve

# ============== Migrations recipes for Copier ==============

# Hidden command to adjust the directory layout on upgrading a project
# created with linkml-project-copier v0.1.x to v0.2.0 or newer.
# Use with care! - It may not work for customized projects.
_post_upgrade_v020: _wsl2_compat_check && _post_upgrade_v020py
  mv docs/*.md docs/elements

_post_upgrade_v020py:
    #!{{shebang}}
    import subprocess
    from pathlib import Path
    # Git move files from folder src to folder dest
    tasks = [
        (Path("src/docs/files"), Path("docs")),
        (Path("src/docs/templates"), Path("docs/templates-linkml")),
        (Path("src/data/examples"), Path("tests/data/")),
    ]
    for src, dest in tasks:
        for path_obj in src.rglob("*"):
            if not path_obj.is_file():
                continue
            file_dest = dest / path_obj.relative_to(src)
            if not file_dest.parent.exists():
                file_dest.parent.mkdir(parents=True)
            print(f"Moving {path_obj} --> {file_dest}")
            subprocess.run(["git", "mv", str(path_obj), str(file_dest)])
    print(
        "Migration to v0.2.x completed! Check the changes carefully before committing."
    )

# ============== Hidden internal recipes ==============

# Show current project status
_status: _wsl2_status_check _check-config
  @echo "Project: {{schema_name}}"
  @echo "Product schema: {{doc_schema_path}}"

# Check project configuration
_check-config:
    #!{{shebang}}
    import os
    schema_name = os.getenv('LINKML_SCHEMA_NAME')
    if not schema_name:
        print('**Project not configured**:\n - See \'.env.public\'')
        exit(1)
    print('Project-status: Ok')

# Update project template
_update-template:
  copier update --trust --skip-answered

# Update LinkML runtime and LinkML to latest versions
_update-linkml:
  uv lock --upgrade-package linkml-runtime --upgrade-package linkml

# Check that LinkML can load and render the product schema
_test-schema:
  uv run gen-yaml {{doc_schema_path}} > /dev/null

# Run Python unit tests with pytest
_test-python:
  uv run python -m pytest

# Add the merged model to docs/schema.
_gen-yaml:
  -mkdir -p {{distrib_schema_path}}
  uv run gen-yaml {{doc_schema_path}} > {{distrib_schema_path}}/{{doc_schema_name}}.yaml

# Overridable recipe to add project-specific artifacts to the distribution schema path
_add-artifacts:

# Run documentation server
_serve:
  uv run mkdocs serve

# Initialize git repository
_git-init:
  git init

# Add files to git
_git-add:
  git add .

# Commit files to git
_git-commit:
  git commit -m 'chore: just setup was run' -a

# Show git status
_git-status:
  git status

# ============== Include project-specific recipes ==============

import "project.justfile"

# ====== Override recipes from above with custom versions =======

# Uncomment the following line to allow duplicate recipe names
#set allow-duplicate-recipes

# Overriding recipes from the root justfile by adding a recipe with the same
# name in an imported file is not possible until a known issue in just is fixed,
# https://github.com/casey/just/issues/2540 - So we need to override them here.
