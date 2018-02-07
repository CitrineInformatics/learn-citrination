#!/bin/bash

for notebook in "AdvancedPif" "AdvancedQueries" "ImportVASP" "IntroQueries" "MLonCitrination" "WorkingWithPIFs"; do
  ./ci/swap_kernel.py ${notebook}.ipynb ${notebook}-swap.ipynb python3
  jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=300 --output tmp.ipynb ${notebook}-swap.ipynb
  echo "Tested ${notebook} -^"
  rm -f tmp.ipynb ${notebook}-swap.ipynb
done

