#!/bin/bash

for notebook in "$@"; do
  ./ci/swap_kernel.py ${notebook}.ipynb ${notebook}-swap.ipynb python3
  jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=300 --output tmp.ipynb ${notebook}-swap.ipynb
  if [ $? -ne 0 ]
  then
    echo "Notebook ${notebook} failed"
    rm -f tmp.ipynb ${notebook}-swap.ipynb
    exit 1
  fi
  rm -f tmp.ipynb ${notebook}-swap.ipynb
done
