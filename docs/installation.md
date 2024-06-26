# Installation

[Poetry](https://github.com/python-poetry/poetry) is used to manage the
python development environment.

A simple way to create an environment with the desired version of python
and poetry is to use
[conda](https://docs.conda.io/en/latest/miniconda.html). E.g.:

    conda create -n fgpyo python=3.6 poetry
    conda activate fgpyo
    poetry install

If, during `poetry install` on Mac OS X errors are
encountered running gcc/clang to build `pybedtools` or other
packages with native code, try setting the following and re-running
\`poetry install\`:

    export CFLAGS="-stdlib=libc++"
