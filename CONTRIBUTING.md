# Contributing

## Installation for Local Development

[`uv`][uv-link] is used to manage the python development environment; [installation instructions for `uv` are here][uv-install-link].

A simple way to create an environment with the desired version of `python` and `uv` is to use a virtual environment.  E.g.:

```console
uv venv --python 3.12 --seed
source .venv/bin/activate
# `--group docs` is required to install `mkdocs` and associated dependencies
# `--group dev` is required to install test and build dependencies
uv pip install --group dev --group docs
```

[uv-link]:         https://docs.astral.sh/uv/
[uv-install-link]: https://docs.astral.sh/uv/getting-started/installation/

## Primary Development Commands

To check and resolve linting issues in the codebase, run:

```console
uv run ruff check --fix fgpyo tests
```

To check and resolve formatting issues in the codebase, run:

```console
uv run ruff format fgpyo tests
```

To check the unit tests in the codebase, run:

```console
uv run pytest --cov=fgpyo --cov-report=html --cov-branch
```

To check the typing in the codebase, run:

```console
uv run mypy fgpyo tests --config=pyproject.toml
```

To re-generate a code coverage report after testing locally, run:

```console
uv run coverage html
```

To check the lock file is up-to-date:

```console
uv lock --check
```

## Building the Documentation

Use `mkdocs` to build and serve the documentation.

```console
uv run mkdocs build --strict
uv run mkdocs serve --watch docs
```

## Creating a Release on PyPI

1. Clone the repository recursively and ensure you are on the `main` (un-dirty) branch
2. Checkout a new branch to prepare the library for release
3. Bump the version of the library to the desired SemVer (in the `pyproject.toml`)
4. Commit the version bump changes with a Git commit message like `chore(release): bump to #.#.#`
5. Push the commit to the upstream remote, open a PR, ensure tests pass, and seek reviews
6. Squash merge the PR
7. Tag the new commit on the main branch of the origin repository with the new SemVer

> NOTE:
> This project follows [Semantic Versioning](https://semver.org/).
> In brief:
> 
> - `MAJOR` version when you make incompatible API changes
> - `MINOR` version when you add functionality in a backwards compatible manner
> - `PATCH` version when you make backwards compatible bug fixes

GitHub Actions will take care of the remainder of the deployment and release process with:

1. Unit tests will be run for safety-sake
2. A source distribution will be built
3. Multi-arch multi-Python binary distributions will be built
4. Assets will be deployed to PyPI with the new SemVer
5. A [Conventional Commit](https://www.conventionalcommits.org/en/v1.0.0/)-aware changelog will be drafted
6. A GitHub release will be created with the new SemVer and the drafted changelog

> WARNING:
> Consider editing the changelog if there are any errors or necessary enhancements.
