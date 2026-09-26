import runpy, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
runpy.run_module('dataset_v2.validate', run_name='__main__')
