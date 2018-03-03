#!/bin/bash

kernel=$1
shift 1

for notebook in "$@"; do
  echo "Evaluating ${notebook} with ${kernel} kernel"
  ./ci/swap_kernel.py ${notebook}.ipynb ${notebook}-swap.ipynb $kernel
  jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=300 --output tmp.ipynb ${notebook}-swap.ipynb
  if [ $? -ne 0 ]
  then
    echo "Notebook ${notebook} failed"
    rm -f tmp.ipynb ${notebook}-swap.ipynb
    exit 1
  fi
  rm -f tmp.ipynb ${notebook}-swap.ipynb
  echo "${notebook} was evaluated successfully"
done
