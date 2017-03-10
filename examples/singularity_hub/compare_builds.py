# Compare Singularity Hub containers

# This is a simple script to use the singularity command line tool to download containers
# (using Singularity, Section 1) and compare build specs (using Singularity Hub API, Section 2) and to
# compare the containers themselves using singularity python (Section 3)

container_names = ['vsoch/singularity-hello-world',
                   'researchapps/quantum_state_diffusion',
                   'vsoch/pefinder']

from singularity.hub.client import Client
from singularity.cli import Singularity
from singularity.package import get_image_hash
from singularity.analysis.compare import compare_container_sets
from singularity.package import content_metadata

import tempfile
import os
import pandas
import shutil

shub = Client()    # Singularity Hub Client
S = Singularity()  # command line client
results = dict()
images = dict()

# Let's keep images in a temporary folder
storage = tempfile.mkdtemp()
os.chdir(storage)

# We will keep a table of information
df = pandas.DataFrame()

for container_name in container_names:
    
    # Retrieve the container based on the name
    collection = shub.get_collection(container_name)
    container_ids = collection['container_set']
    containers = []
    image_set = []
    for container_id in container_ids:
       manifest = shub.get_container(container_id)
       containers.append(manifest)
       image = "%s/%s.img" %(storage,manifest['version'])
       if not os.path.exists(image):
           image = shub.pull_container(manifest,
                                       download_folder=storage,
                                       name=os.path.basename(image))       
       image_set.append(image)
       infos = pandas.DataFrame(content_metadata(image_path=image,S=S))
       infos['container_name'] = "%s-%s" %(container_name,manifest['version'])
       df = df.append(infos)

    images[container_name] = image_set
    results[container_name] = {'collection':collection,
                               'containers':containers}


# Now compare containers
result_folder = '/home/vanessa/Documents/Dropbox/Code/singularity/singularity-python/examples/singularity_hub'
for container_name,image_set in images.items():
    comparisons = compare_container_sets(container_set1=images,
                                         container_set2=images)
    output_file = "%s/comparisondf_%s.tsv" %(result_folder,container_name)
    comparisons.to_csv(output_file,sep="\t")


images = glob("%s/*" %(storage))
comparisons = compare_container_sets(container_set1=images,container_set2=images)

import pickle
result_folder = '/home/vanessa/Documents/Dropbox/Code/singularity/singularity-python/examples/singularity_hub'
pickle.dump(results,open('%s/build_manifests.json' %(result_folder)))
df.to_csv("%s/compare_builds.tsv" %(result_folder),sep="\t")

# Write the table to file
table = ''
for row in df.iterrows():
    table = '''%s
               <tr>
                  <td>%s</td>
                  <td>%s</td>
                  <td>%s</td>
               </tr>
            ''' %(table,row[1]['name'],
                  row[1]['commit'],
                  row[1]['build_time_seconds'],
                  row[1]['hash'],
                  row[1]['size'],
                  row[1]['estimated_os'])


template = open('%s/template.html','r').read()
template.replace('[[TABLE]]',table)
with open('%s/index.html' %(result_folder),'w') as filey:
    filey.writelines(template)

shutil.rmtree(storage)
