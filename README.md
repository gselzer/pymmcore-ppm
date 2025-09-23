# pymmcore-ppm

This package provides an *extension* to the [`pymmcore-gui`](https://github.com/pymmcore-plus/pymmcore-gui).

Current features target use cases within the [Laboratory for Optical and Computational Instrumentation](https://loci.wisc.edu/) at the University of Wisconsin-Madison.

## Usage

### Installation

from pip:

```
TODO
```

from github:

```bash
pip install 'pymmcore-ppm @ git+https://github.com/gselzer/pymmcore-ppm'
```

### Launching

from the command line:
```bash
mmppm
```

from python:
```python
from pymmcore_ppm import run
run()
```

## Development

Developers should use [uv](https://docs.astral.sh/uv/) to create a suitable development environment:

```bash
git clone git@github.com:gselzer/pymmcore-ppm
cd pymmcore-ppm
uv sync
```
