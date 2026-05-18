import sys
sys.path.insert(0, '/usr/local/lib/python3.12/dist-packages')
from swebench.harness.docker_build import build_instance_image
import inspect
sig = inspect.signature(build_instance_image)
print(f'Signature: {sig}')
print(f'Parameters: {list(sig.parameters.keys())}')
