"""Compatibility shim so ``pip install -e .`` works on older pip versions.

All real configuration lives in ``pyproject.toml``; this file only exists because pip < 21.3 cannot
perform an editable install from a pyproject-only, src-layout project.
"""

from setuptools import setup

setup()
