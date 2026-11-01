import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
os.environ['PYTHONPYCACHEPREFIX'] = str(ROOT/'tmp/pycache')
sys.path.insert(0,str(ROOT))
suite = unittest.defaultTestLoader.discover(str(ROOT/'tests'))
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
