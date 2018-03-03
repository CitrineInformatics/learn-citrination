#!/usr/bin/env python

from sys import argv
import json

fname_in = argv[1]
fname_out = argv[2]
kernel = argv[3]

with open(fname_in, "r") as f:
    notebook = json.load(f)

notebook["metadata"]["kernelspec"]["name"] = kernel

with open(fname_out, "w") as f:
    json.dump(notebook, f)
