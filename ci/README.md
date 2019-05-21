# Continuous Integration

These notebooks are automatically tested with every commit and PR using 
[travis](https://travis-ci.org/CitrineInformatics/learn-citrination),
as configured [here](../.travis.yml).
The environment is loaded with an encrypted api key in the environment as `CITRINATION_API_KEY`.
The [`test_notebooks.sh`](./test_notebooks.sh) runs the notebook using nbconvert and checks the
exit code to detect failures.
The [`swap_kernel.py`](./swap_kernel.py) file is used to toggle between python2 and python3.

Contributions of new notebooks to this repository should use the `CITRINATION_API_KEY`,
and add a testing line to the [travis config file](../.travis.yml).

