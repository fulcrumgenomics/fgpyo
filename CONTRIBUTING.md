# Contributing

## Installation for Local Development

[Poetry][poetry-link] is used to manage the python development environment. 

A simple way to create an environment with the desired version of python and poetry is to use [conda][conda-link].  E.g.:

```bash
conda create -n fgpyo -c conda-forge "python>=3.9" poetry
conda activate fgpyo

# --all-extras is required to install `mkdocs` and associated dependencies,
# which are required for development 
poetry install --all-extras
```

[rtd-link]:    http://fgpyo.readthedocs.org/en/stable
[poetry-link]: https://github.com/python-poetry/poetry
[conda-link]:  https://docs.conda.io/en/latest/miniconda.html

## Primary Development Commands

To check and resolve linting issues in the codebase, run:

```console
poetry run ruff check --fix
```

To check and resolve formatting issues in the codebase, run:

```console
poetry run ruff format
```

To check the unit tests in the codebase, run:

```console
poetry run pytest
```

To check the typing in the codebase, run:

```console
poetry run mypy
```

To generate a code coverage report after testing locally, run:

```console
poetry run coverage html
```

To check the lock file is up to date:

```console
poetry check --lock
```

## Shortcut Task Commands

To be able to run shortcut task commands, first install the Poetry plugin [`poethepoet`](https://poethepoet.natn.io/index.html):

```console
poetry self add 'poethepoet[poetry_plugin]'
```

> NOTE:
> Upon the release of Poetry [v2.0.0](https://github.com/orgs/python-poetry/discussions/9793#discussioncomment-11043205), Poetry will automatically support bootstrap installation of [project-specific plugins](https://github.com/python-poetry/poetry/pull/9547) and installation of the task runner will become automatic for this project.
> The `pyproject.toml` syntax will be:
> 
> ```toml
> [tool.poetry]
> requires-poetry = ">=2.0"
> 
> [tool.poetry.requires-plugins]
> poethepoet = ">=0.29"
> ```

###### For Running Individual Checks

```console
poetry task check-lock
poetry task check-format
poetry task check-lint
poetry task check-tests
poetry task check-typing
```

###### For Running All Checks

```console
poetry task check-all
```

###### For Running Individual Fixes

```console
poetry task fix-format
poetry task fix-lint
```

###### For Running All Fixes

```console
poetry task fix-all
```

###### For Running All Fixes and Checks

```console
poetry task fix-and-check-all
```


## Building the Documentation

Use `mkdocs` to build and serve the documentation.

```console
poetry run mkdocs build && poetry run mkdocs serve
```

## Creating a Release on PyPI

1. Clone the repository recursively and ensure you are on the `main` (un-dirty) branch
2. Checkout a new branch to prepare the library for release
3. Bump the version of the library to the desired SemVer with `poetry version #.#.#`
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