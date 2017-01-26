# learn-citrination

Demos and tutorials for API access to Citrination.com

## Requirements

Most of these tutorials are jupyter notebooks backed by a python3 kernel.  You'll need:
 - python3 with Jupyter.  [Anaconda](https://www.continuum.io/downloads) is highly recommended.
 - `pypif` and `citrination_client` packages:
 
 ```pip install pypif citrination_client dfttopif```

 - A valid citrination client API key set in your environment variables:
   0. [Create an account](https://citrination.com/users/sign_up) on Citrination (if you don't already have one)
   1. Go to your [account page](https://stage.citrination.com/users/edit) and look for "API Key"
   2. Add the key to your environment.  If you use a bash shell, the command is:
   
   ```export CITRINATION_API_KEY=<your key copied from the website>```
   
   You can add this command to your `.bashrc` file to automatically set the API key in each new session.
   
   The API key functions as the password for the client, so its important to keep it private.  Its a good practice to put it in your environment instead of in the source code to help avoid unintentional sharing or publication of your API key.

## References

The example data used in these tutorials is drawn from:

 * [Alloy Database](http://alloy.phys.cmu.edu/) by Mihalkovic, Widom, and coworkers
