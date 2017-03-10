#!/usr/bin/env python

'''
utils.py: part of singularity package

'''

import collections
import os
import re
import requests

import shutil
import json
import simplejson
import singularity.__init__ as hello
from singularity.logman import bot
import sys

import subprocess

import tempfile
import zipfile


# Python less than version 3 must import OSError
if sys.version_info[0] < 3:
    from exceptions import OSError

# raw_input renamed to input in python 3
try:
    input = raw_input
except NameError:
    pass


######################################################################################
# Local commands and requests
######################################################################################


def check_install(software=None):
    '''check_install will attempt to run the singularity command, and return an error
    if not installed. The command line utils will not run without this check.
    '''    
    if software == None:
        software = "singularity"
    cmd = [software,'--version']
    version = run_command(cmd,error_message="Cannot find %s. Is it installed?" %software)
    if version != None:
        bot.logger.info("Found %s version %s",software.upper(),version)
        return True
    else:
        return False


def get_installdir():
    '''get_installdir returns the installation directory of the application
    '''
    return os.path.abspath(os.path.dirname(hello.__file__))


def get_script(script_name):
    '''get_script will return a script_name, if it is included in singularity/scripts,
    otherwise will alert the user and return None
    :param script_name: the name of the script to look for
    '''
    install_dir = get_installdir()
    script_path = "%s/scripts/%s" %(install_dir,script_name)
    if os.path.exists(script_path):
        return script_path
    else:
        bot.logger.error("Script %s is not included in singularity-python!", script_path)
        return None

def getsudo():
    sudopw = input('[sudo] password for %s: ' %(os.environ['USER']))
    os.environ['pancakes'] = sudopw
    return sudopw



def run_command(cmd,error_message=None,sudopw=None,suppress=False):
    '''run_command uses subprocess to send a command to the terminal.
    :param cmd: the command to send, should be a list for subprocess
    :param error_message: the error message to give to user if fails, 
    if none specified, will alert that command failed.
    :param execute: if True, will add `` around command (default is False)
    :param sudopw: if specified (not None) command will be run asking for sudo
    '''
    if sudopw == None:
        sudopw = os.environ.get('pancakes',None)

    if sudopw != None:
        cmd = ' '.join(["echo", sudopw,"|","sudo","-S"] + cmd)
        if suppress == False:
            pipe = os.popen(cmd)
            output = pipe.read().strip('\n')
            pipe.close()
        else:
            output = cmd
            os.system(cmd)
    else:
        try:
            pipe = subprocess.Popen(cmd,stdout=subprocess.PIPE)
            output, err = pipe.communicate()
            pipe.close()
        except OSError as error: 
            if error.errno == os.errno.ENOENT:
                bot.logger.error(error_message)
            else:
                bot.logger.error(err)
            return None
    
    return output


############################################################################
## FILE OPERATIONS #########################################################
############################################################################

def zip_dir(zip_dir, zip_name, output_folder=None):
    '''zip_dir will zip up and entire zip directory
    :param folder_path: the folder to zip up
    :param zip_name: the name of the zip to return
    :output_folder:
    '''
    tmpdir = tempfile.mkdtemp()
    output_zip = "%s/%s" %(tmpdir,zip_name)
    zf = zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED, allowZip64=True)
    for root, dirs, files in os.walk(zip_dir):
        for file in files:
            zf.write(os.path.join(root, file))
    zf.close()
    if output_folder != None:
        shutil.copyfile(output_zip,"%s/%s"%(output_folder,zip_name))
        shutil.rmtree(tmpdir)
        output_zip = "%s/%s"%(output_folder,zip_name)
    return output_zip


def zip_up(file_list,zip_name,output_folder=None):
    '''zip_up will zip up some list of files into a package (.zip)
    :param file_list: a list of files to include in the zip.
    :param output_folder: the output folder to create the zip in. If not 
    :param zip_name: the name of the zipfile to return.
    specified, a temporary folder will be given.
    '''
    tmpdir = tempfile.mkdtemp()
   
    # Make a new archive    
    output_zip = "%s/%s" %(tmpdir,zip_name)
    zf = zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED, allowZip64=True)

    # Write files to zip, depending on type
    for filename,content in file_list.items():

        bot.logger.debug("Adding %s to package...", filename)

        # If it's the files list, move files into the archive
        if filename.lower() == "files":
            if not isinstance(content,list): 
                content = [content]
            for copyfile in content:
                zf.write(copyfile,os.path.basename(copyfile))
        # If it's a list, write to new file, and save
        elif isinstance(content,list):
            filey = write_file("%s/%s" %(tmpdir,filename),"\n".join(content))
            zf.write(filey,filename)
            os.remove(filey)
        # If it's a dict, save to json
        elif isinstance(content,dict):
            filey = write_json(content,"%s/%s" %(tmpdir,filename))
            zf.write(filey,filename)
            os.remove(filey)
        # If it's a string, do the same
        elif isinstance(content,str):
            filey = write_file("%s/%s" %(tmpdir,filename),content)
            zf.write(filey,filename)
            os.remove(filey)
        # Otherwise, just write the content into a new archive
        elif isinstance(content,bytes):
            filey = write_file("%s/%s" %(tmpdir,filename),content.decode('utf-8'))
            zf.write(filey,filename)
            os.remove(filey)
        else: 
            zf.write(content,filename)

    # Close the zip file    
    zf.close()

    if output_folder != None:
        shutil.copyfile(output_zip,"%s/%s"%(output_folder,zip_name))
        shutil.rmtree(tmpdir)
        output_zip = "%s/%s"%(output_folder,zip_name)

    return output_zip


def write_file(filename,content,mode="w"):
    '''write_file will open a file, "filename" and write content, "content"
    and properly close the file
    '''
    with open(filename,mode) as filey:
        filey.writelines(content)
    return filename


def write_json(json_obj,filename,mode="w",print_pretty=True):
    '''write_json will (optionally,pretty print) a json object to file
    :param json_obj: the dict to print to json
    :param filename: the output file to write to
    :param pretty_print: if True, will use nicer formatting   
    '''
    with open(filename,mode) as filey:
        if print_pretty == True:
            filey.writelines(simplejson.dumps(json_obj, indent=4, separators=(',', ': ')))
        else:
            filey.writelines(simplejson.dumps(json_obj))
    return filename


def read_file(filename,mode="r"):
    '''write_file will open a file, "filename" and write content, "content"
    and properly close the file
    '''
    with open(filename,mode) as filey:
        content = filey.readlines()
    return content


def read_json(filename,mode='r'):
    '''read_json reads in a json file and returns
    the data structure as dict.
    '''
    with open(filename,mode) as filey:
        data = json.load(filey)
    return data


############################################################################
## OTHER MISC. #############################################################
############################################################################


def calculate_folder_size(folder_path,truncate=True):
    '''calculate_folder size recursively walks a directory to calculate
    a total size (in MB)
    :param folder_path: the path to calculate size for
    :param truncate: if True, converts size to an int
    '''
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filey in filenames:
            file_path = os.path.join(dirpath, filey)
            if os.path.isfile(file_path) and not os.path.islink(file_path):
                total_size += os.path.getsize(file_path) # this is bytes
    size_mb = total_size / 1000000
    if truncate == True:
        size_mb = int(size_mb)
    return size_mb


def remove_unicode_dict(input_dict):
    '''remove unicode keys and values from dict, encoding in utf8
    '''
    #if isinstance(input_dict, basestring):
    #    return str(input_dict)
    if isinstance(input_dict, collections.Mapping):
        return dict(map(remove_unicode_dict, input_dict.iteritems()))
    elif isinstance(input_dict, collections.Iterable):
        return type(input_dict)(map(remove_unicode_dict, input_dict))
    else:
        return input_dict


def update_dict(input_dict,key,value):
    '''update_dict will update lists in a dictionary. If the key is not included,
    if will add as new list. If it is, it will append.
    :param input_dict: the dict to update
    :param value: the value to update with
    '''
    if key in input_dict:
        input_dict[key].append(value)
    else:
        input_dict[key] = [value]
    return input_dict


def update_dict_sum(input_dict,key,increment=None,initial_value=None):
    '''update_dict sum will increment a dictionary key 
    by an increment, and add a value of 0 if it doesn't exist
    :param input_dict: the dict to update
    :param increment: the value to increment by. Default is 1
    :param initial_value: value to start with. Default is 0
    '''
    if increment == None:
        increment = 1

    if initial_value == None:
        initial_value = 0

    if key in input_dict:
        input_dict[key] += increment
    else:
        input_dict[key] = initial_value
    return input_dict


def format_container_name(name,special_characters=None):
    '''format_container_name will take a name supplied by the user,
    remove all special characters (except for those defined by "special-characters"
    and return the new image name.
    '''
    if special_characters == None:
        special_characters = []
    return ''.join(e.lower() for e in name if e.isalnum() or e in special_characters)


def remove_uri(container):
    '''remove_uri will remove docker:// or shub:// from the uri
    '''
    return container.replace('docker://','').replace('shub://','')


def download_repo(repo_url,destination,commit=None):
    '''download_repo
    :param repo_url: the url of the repo to clone from
    :param destination: the full path to the destination for the repo
    '''
    command = "git clone %s %s" %(repo_url,destination)
    os.system(command)
    return destination

