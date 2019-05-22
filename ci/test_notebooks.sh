#!/bin/bash


## Pick a kernel and use it to run notebooks on the command line, i.e.
## ./test_notebooks.sh KERNEL_NAME NOTEBOOK_NAME [NEXT_NOTEBOOK_NAME [ANOTHER_NOTEBOOK_NAME ...]]

# the kernel name is the first argument
kernel=$1
# move down the argument list to the list of notebooks
shift 1

# foreach notebook in the argument list
for notebook in "$@"; do
  echo "Evaluating ${notebook} with ${kernel} kernel"
  # set the kernel
  ./ci/swap_kernel.py ${notebook}.ipynb ${notebook}-swap.ipynb $kernel
  # execute the notebook on the command line
  jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=300 --output tmp.ipynb ${notebook}-swap.ipynb

  # check the exit code. non-zero is a failure
  if [ $? -ne 0 ]
  then
    echo "Notebook ${notebook} failed"
    rm -f tmp.ipynb ${notebook}-swap.ipynb
    exit 1
  fi
  rm -f tmp.ipynb ${notebook}-swap.ipynb
  echo "${notebook} was evaluated successfully"
done
