# Installation

[`uv`][uv-link] is used to manage the python development environment; [installation instructions for `uv` are here][uv-install-link].

A simple way to create an environment with the desired version of `python` and `uv` is to use a virtual environment.  E.g.:

```console
uv venv --python 3.12
source .venv/bin/activate
# --group is required to install `mkdocs` and associated dependencies,
# which are required for development
uv pip install --group dev --group docs
```

[rtd-link]:        http://fgpyo.readthedocs.org/en/stable
[uv-link]:         https://docs.astral.sh/uv/
[uv-install-link]: https://docs.astral.sh/uv/getting-started/installation/

If, during `uv pip install` on Mac OS X errors are
encountered running gcc/clang to build `pybedtools` or other
packages with native code, try setting the following and re-running
\`uv pip install\`:

    export CFLAGS="-stdlib=libc++"
