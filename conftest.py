"""Permite que pytest encuentre los paquetes de 04_src (parser, normalizer, ...)
sin tener que instalar el proyecto con `pip install -e .` primero.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "04_src"))
