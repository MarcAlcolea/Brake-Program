"""Brake Design Studio — FSAE brake system design tool.

The importable Python package is still named ``brakelab`` (internal identifier); the product name
shown to users is "Brake Design Studio".

Layers (see docs/architecture.md):
  core        pure calculation engine (no GUI/IO)
  analyses    pluggable studies over (config, engine)
  thermal     rotor thermal analysis (future)
  persistence JSON save/load
  reporting   PDF reports
  app         PySide6 GUI

Run the GUI with ``python -m brakelab``; run a config headlessly with ``python -m brakelab.cli``.
"""

__version__ = "0.1.0"
