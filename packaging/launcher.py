"""Entry script for the frozen (PyInstaller) Brake Design Studio app.

PyInstaller analyses this file to discover the whole application; at runtime it simply
starts the GUI. Source-tree users run ``python -m brakelab`` instead.
"""

import os
import sys

# PyInstaller's matplotlib runtime hook points MPLCONFIGDIR at a throwaway temp dir, which
# forces a slow font-cache rebuild on every launch. Give it a persistent per-user home
# instead (must happen before matplotlib is first imported).
from brakelab.persistence.library import app_data_dir

_mpl_dir = app_data_dir() / "matplotlib"
_mpl_dir.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(_mpl_dir)

from brakelab.app.main import run

if __name__ == "__main__":
    sys.exit(run())
