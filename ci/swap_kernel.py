#!/usr/bin/env python

from sys import argv
import json

## This script loads a jupyter notebook,
## sets the kernel name, and
## writes the result to a new file

# file name of the jupyter notebook to load
fname_in = argv[1]
# file name to which to write the jupyter notebook
fname_out = argv[2]
# name of the kernel.  "python2" for python 2.x and "python3" for python 3.x
kernel = argv[3]

# jupyter notebooks are just json files
with open(fname_in, "r") as f:
    notebook = json.load(f)

# this is the field that defines the kernel, as a string
notebook["metadata"]["kernelspec"]["name"] = kernel

# write it back out
with open(fname_out, "w") as f:
    json.dump(notebook, f)
