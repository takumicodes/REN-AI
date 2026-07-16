import subprocess
from importlib.util import spec_from_file_location, module_from_spec

# Download and install the library
subprocess.run([sys.executable, '-m', 'pip', 'install', 'pynotifier'])

speak("[DONE]")