# Release Guide

This document describes how to publish the `kfp-components` package and how to react if a release needs to be withdrawn. Follow every step to keep automation, downstream consumers, and PyPI in sync.

## Versioning Strategy

We use [Semantic Versioning](https://semver.org/) for `kfp-components`.

- **Major** (`vX.0.0`): Breaking changes or alignment with a new Kubeflow Pipelines major release. Coordinate with the Pipelines Working Group before cutting a major.
- **Minor** (`vX.Y.0`): New components, features, or dependency bumps that stay backward compatible.
- **Patch** (`vX.Y.Z`): Bug fixes, metadata refreshes, or documentation-only updates.

All git tags **must be prefixed with `v`** (for example: `v1.11.0`). The GitHub Actions workflows ignore tags without that prefix, so `1.11.0` will not build or publish artifacts.

## Pre-release Checklist

1. Confirm the main branch is healthy: CI is green and `uv build` succeeds locally.
2. Ensure all required documentation updates (including changelog entries if applicable) are committed.
3. Make sure `pyproject.toml` already contains the release metadata you intend to publish (name, classifiers, dependencies).

## Release Procedure

1. **Update the version** in `pyproject.toml` under the `[project]` section.
2. **Commit** the change with a message such as `chore: bump version to v1.11.1`.
3. **Tag the commit** using the `v` prefix:

   ```bash
   git tag v1.11.1
   git push origin main
   git push origin v1.11.1
   ```

4. Wait for GitHub Actions to finish (details below). Publish release notes on GitHub after the workflow succeeds.

## GitHub Actions Automation

Two workflows collaborate to ship a release.

### Build Validation (`.github/workflows/build-packages.yml`)

- **Trigger**: pushes to `main` and pull requests targeting `main`.
- **Behavior**:
  - Uses a Python matrix (currently 3.11 and 3.13) to build, validate, and test the package.
  - Uploads the artifacts for inspection. No publish occurs.
- **What it does**:
  - Builds wheel and source distributions with `uv build`.
  - Validates wheel contents and metadata.
  - Creates an isolated virtual environment and verifies that `kfp-components` installs and imports correctly.
  - Uploads the build artifacts as workflow artifacts for traceability.

### Release Pipeline (`.github/workflows/release.yml`)

- **Trigger**: pushes to tags that match `vX.Y.Z` (semantic versioning with a leading `v`).
- **How it works**:
  - Calls the reusable `build-packages.yml` workflow with a single Python version (3.11) and `publish_packages=true`.
  - The reusable workflow switches into “release mode,” which:
    - Installs `build` and `twine`.
    - Builds an sdist (`python -m build --sdist`).
    - Unpacks the sdist into a temporary directory.
    - Rebuilds the wheel using the unpacked sdist contents.
    - Runs `twine check` on the sdist and wheel.
    - Performs the same validation and import smoke tests as the main workflow.
    - Uploads the artifacts for auditing.
    - Publishes the release to PyPI via Trusted Publishing (GitHub Actions OIDC), so no manual credential management or `twine upload` step is required.

If the workflow fails, do not push a PyPI release. Fix the failure, retag (or tag a new patch version), and rerun the pipeline.

## Rollback Procedure (Yanking a Release)

PyPI does **not** support deleting releases. If a published version is broken:

1. Sign in to [pypi.org](https://pypi.org/) with an account that has maintainer or owner rights on `kfp-components`.
2. Navigate to the project → **Release history**, select the release that needs to be withdrawn, and choose **Yank release**.
3. Provide a brief explanation for the yank (PyPI will display this note to installers) and confirm.
4. Communicate the issue in GitHub (discussion or release notes) and plan a follow-up patch release (for example `v1.11.2`) with the fix.
5. Tag and publish the new patch release following the standard procedure.

Do **not** attempt to reuse a yanked version number. Always increment the patch version for the corrective release.
