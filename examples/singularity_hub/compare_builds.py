# Compare Singularity Hub containers

# This is a simple script to use the singularity command line tool to download containers
# (using Singularity, Section 1) and compare build specs (using Singularity Hub API, Section 2) and to
# compare the containers themselves using singularity python (Section 3)

container_names = ['vsoch/singularity-hello-world',
                   'researchapps/quantum_state_diffusion',
                   'vsoch/pefinder']

from singularity.hub.client import Client
from singularity.cli import Singularity
import tempfile
import os

shub = Client()    # Singularity Hub Client
S = Singularity()  # Singularity command line client
results = dict()

# Let's keep images in a temporary folder
storage = tempfile.mkdtemp()
os.chdir(storage)

for container_name in container_names:
    
    # Retrieve the container based on the name
    collection = shub.get_collection(container_name)
    container_ids = collection['container_set']
    containers = []
    for container_id in container_ids:
       container = shub.get_container(container_id)
       containers.append(container)
       # Download the specific container
       commit = container['version']
       S.pull("shub://%s:%s" %(container_name,commit))

    results[container_name] = {'collection':collection,
                               'containers':containers}

