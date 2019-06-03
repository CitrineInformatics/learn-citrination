![Citrine banner](https://raw.githubusercontent.com/CitrineInformatics/community-tools/master/templates/fig/citrine_banner_2.png)

# learn-citrination

Demos and tutorials for API access to [Citrination](https://citrination.com/).

Documentation for the **Python Citrination Client (PyCC)** can be found [here](http://citrineinformatics.github.io/python-citrination-client/index.html).


## Contents
The examples are grouped based on the functionality and tools they aim to teach. Examples include:
* Guides to the [Citrination API](citination_api_examples) with Python notebooks.
* Guides to the [Citrination web UI](citrination_ui_examples) with screenshots in Markdown files.
* The [matminer](matminer_examples) package and how it interfaces with Citrination.
* [Synthetic data](synthetic_data_examples) to demonstrate data summary statistics on Citrination.


## Requirements

Most of these tutorials are [Jupyter](https://jupyter.org/) notebooks backed by a [Python 3](https://docs.python.org/3/whatsnew/index.html) kernel.  You'll need:
 - Python 3 with Jupyter. [Anaconda](https://www.continuum.io/downloads)/[Miniconda](https://docs.conda.io/en/latest/miniconda.html) is highly recommended.
 - Additional packages, which can be installed using `pip`:   
 ```
 pip install -U -r requirements.txt   
 ```   

 or `conda`:   
 ```
 while read requirement; do conda install --yes $requirement; done < requirements.txt
 ```   


## API Key  
You will need a valid Citrination Client [API key](http://citrineinformatics.github.io/python-citrination-client/tutorial/initialization.html) set in your [environment variables](https://en.wikipedia.org/wiki/Environment_variable):  
1. [Create an account](https://citrination.com/users/sign_up) on Citrination (if you don't already have one).
2. Go to your [account page](https://citrination.com/users/edit) and look for "API Key."
3. Add the key to your environment.
    * On MacOS, open your `.bash_profile` and add the line
    ```
    export CITRINATION_API_KEY="your_key_copied_from_the_website"
    ```
    Each new Terminal window you open will have the key loaded automatically.

    * On Windows, open your Command Prompt / Anaconda Prompt and enter the line
    ```
    setx CITRINATION_API_KEY "your_key_copied_from_the_website"
    ```
    Each new Prompt you open will have the key loaded automatically.

The API key functions as the password for the client, so it's important to keep it private.  Therefore, we put it in your system environment instead of in the source code to help avoid unintentional sharing or publication of your API key.


## Additional Resources

* The [example data](citrination_api_examples/tutorial_sequence/example_data) used in these tutorials are drawn from: [Alloy Database](http://alloy.phys.cmu.edu/) by Mihalkovic, Widom, and coworkers.

* The band gap data used in these tutorials are from [Strehlow and Cook, *J Phys Chem Ref Data*, **2** (1973)](https://doi.org/10.1063/1.3253115).

* [More programmatic tools](https://github.com/CitrineInformatics/community-tools) have also been developed by the Citrine Community team.
