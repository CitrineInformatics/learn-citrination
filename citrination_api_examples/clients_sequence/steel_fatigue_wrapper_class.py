'''
Authors: Eddie Kim, Enze Chen, Nils Persson
This file contains wrapper functions that are used in the sequential learning
API tutorial notebook. Detailed docstrings with method fuctions and parameters
are given below.
'''

# Standard packages
import os
from uuid import uuid4
from time import time, sleep

# Third party packages
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Citrine packages
from citrination_client import *
from citrination_client.models.design import Target
from citrination_client.views.data_view_builder import DataViewBuilder
from pypif import pif
from pypif.obj import *


def verify_client(client):
    '''
    Verify that the Client is able to create datasets.

    :param client: An instance of CitrinationClient.
    :return: None.
    '''
    dataset_id = None
    try:
        dataset = client.data.create_dataset(
            name='Test valid API key '+str(uuid4()),
            description='This empty dataset was created to test the Client connection.')
        dataset_id = dataset.id
    except:
        print("The Client could not connect.\nPlease double check the deployment name and API key.")
        return
    print("Client created successfully!")
    client.data.delete_dataset(dataset_id=dataset_id)
    return


def get_steel_dataset(client, orig_dataset_id):
    '''
    Retrieve and format the steel fatigue dataset as a DataFrame.

    :param client: An instance of CitrinationClient.
    :param orig_dataset_id: An int representing the dataset ID.
    :return df_steel: A pandas DataFrame for the dataset.
    '''
    dataset_json = client.data.get_dataset_files(orig_dataset_id)[0]
    df = pd.read_json(dataset_json._url)

    # Create Composition and Property columns and combine into one DataFrame
    df_form = df['composition'].apply(lambda dl: pd.Series({d['element']:d['actualWeightPercent']['value'] for d in dl}))
    df_proc = df['properties'].apply(lambda dl: pd.Series({d['name']:d['scalars'][0]['value'] for d in dl}))
    df_steel = pd.concat([df_form, df_proc], axis=1)

    return df_steel


def split_dataset(client, dataset_id, target_col, target_max,
                  num_train = 20, random_seed = 1):
    '''
    Splits an existing dataset such that num_train entries with
    target_col below target_max have their value of target_col
    retained, while the rest have it redacted.

    :param client: Client API object to pass in.
    :param dataset_id: An int representing the ID of dataset to split.
    :param target_col: A string for column name to filter and split on.
    :param target_max: Max float value of target_col to allow in training set.
    :param num_train: An int for the number of training points to keep.
    :param random_seed: A random seed (int) to fix things for testing.
    :return all_pifs: A list of PIF Systems.
    '''

    # Get PIFs with Fatigue Strength above cutoff
    system_query_high = PifSystemReturningQuery(
        size=9999,
        query=DataQuery(
            dataset=DatasetQuery(
                id=Filter(
                    equal=dataset_id)),
            system=PifSystemQuery(
                properties=PropertyQuery(
                    name=FieldQuery(filter=Filter(equal=target_col)),
                    value=FieldQuery(filter=Filter(min=target_max+1e-6))
                )
            )
        )
    )

    query_result_high = client.search.pif_search(system_query_high)
    print('Entries in top split:', query_result_high.total_num_hits)

    # Get PIFs with Fatigue Strength below cutoff
    system_query_low = PifSystemReturningQuery(
        size=9999,
        query=DataQuery(
            dataset=DatasetQuery(
                id=Filter(
                    equal=dataset_id)),
            system=PifSystemQuery(
                properties=PropertyQuery(
                    name=FieldQuery(filter=Filter(equal=target_col)),
                    value=FieldQuery(filter=Filter(max=target_max))
                )
            )
        )
    )

    query_result_low = client.search.pif_search(system_query_low)
    print('Entries in bottom split:', query_result_low.total_num_hits)

    # Choose some number of the low values to use as training points
    # np.random.seed(random_seed)
    low_hits = query_result_low._hits
    np.random.shuffle(low_hits)
    low_hits_split = np.split(low_hits, [num_train])
    train_pifs = [h._system for h in low_hits_split[0]]
    unmeasured_pifs = [h._system for h in low_hits_split[1]] \
                    + [h._system for h in query_result_high._hits]
    print("{} train PIFs and {} possible candidate PIFs.".format(
        len(train_pifs), len(unmeasured_pifs)))

    # Redact the target_col values from the "unmeasured" candidates
    for system in unmeasured_pifs:
        fatigue = [p for p in system.properties if p._name == 'Fatigue Strength'][0]
        fatigue.scalars[0]._value = None

    all_pifs = train_pifs + unmeasured_pifs
    return all_pifs


def upload_data_and_get_id(client, dataset_name, dataset_local_fpath,
                           create_new_version = False, given_dataset_id = None):
    '''
    Uploads data to a new/given dataset and returns its ID.

    :param client: CitrinationClient API object to pass in.
    :param dataset_name: Name of dataset as a string.
    :param dataset_local_fpath: Local data filepath as a string.
    :param create_new_version: Boolean flag for whether or not to make a new version.
    :param given_dataset_id: ID (int) if using existing dataset, defaults to None.
    :return dataset_id: Integer ID of the dataset.
    '''

    if given_dataset_id is None:
        dataset = client.data.create_dataset(dataset_name)
        dataset_id = dataset.id
    else:
        dataset_id = given_dataset_id
        if create_new_version:
            client.data.create_dataset_version(dataset_id)

    # Guard against AWS timeout
    start = time()
    timeout = 240
    while time() - start < timeout:
        sleep(1)
        try:
            print('Uploading data...')
            client.data.upload(dataset_id, dataset_local_fpath)
            break
        except:
            if time() - start >= timeout:
                raise RuntimeError("Possible AWS timeout, try re-running.")
            continue

    _wait_on_ingest(client, dataset_id, wait_time=15, print_output=True)
    assert (client.data.matched_file_count(dataset_id) >= 1), "Upload failed."
    return dataset_id


def build_view_and_get_id(client, dataset_id, view_name, input_keys, output_keys,
                          ignore_keys = [], view_desc = '', wait_time = 2,
                          print_output = False, model_type = 'default'):
    '''
    Builds a new data view and returns the view ID.

    :param client: CitrinationClient object.
    :param dataset_id: Integer ID of the dataset to build data view from.
    :param view_name: Name of the new view as a string.
    :param input_keys: Input key names as a list of strings.
    :param output_keys: Output key names as a list of strings.
    :param ignore_keys: Ignore (dummy) key names in this list of strings.
    :param view_desc: String description for the view, defaults to ''.
    :param wait_time: Wait time in seconds (int) before polling API.
    :param print_output: Boolean flag for whether or not to print outputs.
    :param model_type: 'default' or 'linear' ML model.
    :return dv_id: Integer ID of the data view.
    '''

    dv_builder = DataViewBuilder()
    dv_builder.dataset_ids([str(dataset_id)])
    dv_builder.model_type(model_type)

    for key_name in input_keys:
        if 'formula' in key_name:
            desc_x = InorganicDescriptor(key=key_name,
                                         threshold=1)
            dv_builder.add_descriptor(descriptor=desc_x,
                                      role='input')
        else:
            desc_x = RealDescriptor(key=key_name,
                                    lower_bound=-9999.0,
                                    upper_bound=9999.0)
            dv_builder.add_descriptor(desc_x, role='input')


    for key_name in output_keys:
        desc_y = RealDescriptor(key=key_name,
                                lower_bound=-9999.0,
                                upper_bound=9999.0)
        dv_builder.add_descriptor(desc_y, role='output')

    for key_name in ignore_keys:
        desc_i = RealDescriptor(key=key_name,
                                lower_bound=-9999.0,
                                upper_bound=9999.0)
        dv_builder.add_descriptor(desc_i, role='ignore')

    dv_config = dv_builder.build()

    _wait_on_ingest(client, dataset_id, wait_time, print_output)

    dv_id = client.data_views.create(
        configuration=dv_config,
        name=view_name,
        description=view_desc)

    return dv_id


def _wait_on_ingest(client, dataset_id, wait_time, print_output = True):
    '''
    Utility function to check for data ingest completion.

    :param client: CitrinationClient API object.
    :param dataset_id: Integer ID for the dataset to check.
    :param wait_time: Wait time in seconds (int) before polling API again.
    :param print_output: Boolean flag for whether to display status messages.
    :return: None.
    '''

    sleep(wait_time)
    while (client.data.get_ingest_status(dataset_id) != "Finished"):
        if print_output:
            print("Waiting for data ingest to complete...")
        sleep(wait_time)
    sleep(2)


def _wait_on_data_view(client, view_id, wait_time, print_output = True):
    '''
    Utility function to check for data view creation completion.

    :param client: CitrinationClient API object.
    :param view_id: Integer ID for the data view to check.
    :param wait_time: Wait time in seconds (int) before polling API again.
    :param print_output: Boolean flag for whether to display status messages.
    :return: None.
    '''

    sleep(wait_time)
    while True:
        sleep(wait_time)
        design_status = client.data_views.get_data_view_service_status(view_id)
        if (design_status.experimental_design.ready and
            design_status.predict.event.normalized_progress == 1.0):
            if print_output:
                print("Design ready.")
            break
        else:
            print("Waiting for design services...")
    sleep(2)


def candidates_to_df(candidates):
    '''
    This function turns design candidates into a DataFrame.

    :param candidates: A list of materials candidates output from design runs.
    :return df_cand: A pandas DataFrame of the candidates.
    '''

    df_cand = pd.DataFrame(candidates)
    df_cand[list(df_cand['descriptor_values'].iloc[0].keys())] = \
        df_cand['descriptor_values'].apply(pd.Series)
    df_cand = df_cand.drop(['descriptor_values', 'constraint_likelihoods'], axis=1)
    for col in df_cand.columns:
        try:
            df_cand[col] = df_cand[col].astype(float)
        except:
            pass
    return df_cand


def query_results_to_df(query_result):
    '''
    This function puts query results from the SearchClient into a pandas DataFrame.

    :param query_result: Query results from the SearchClient.
    :return df_query: A pandas DataFrame with data from the query results.
    '''
    try:
        query_result_list = query_result._hits
    except:
        query_result_list = query_result

    result_list = [{p._name:p._scalars[0]._value for p in h._system.properties}
                   for h in query_result_list]
    formula_list = [{c._element:c._actual_weight_percent._value for c in h._system._composition}
                    for h in query_result_list]
    full_results_dict = [{**d1, **d2} for d1,d2 in zip(formula_list, result_list)]
    df_query = pd.DataFrame(full_results_dict).astype(float)
    return df_query


class SL_run:
    '''
    This class wraps the various steps of sequential learning to facilitate
    running multiple SL iterations.
    '''
    def __init__(self, client, view_id, dataset_id, orig_dataset_id,
                 all_dataset_cols, target, score_type,
                 design_effort = 25, wait_time = 10,
                 sampler = 'Default', print_output = True):
        '''
        Constructor.

        :param client: CitinationClient object.
        :param view_id: Integer ID of data view.
        :param dataset_id: Integer ID of dataset.
        :param orig_dataset_id: Integer ID of original dataset with all
            measurements filled in.
        :param all_dataset_cols: Full list of string column names expected for
            measurements.
        :param target: A list of string for the target property and optimization
            objective ('Min' or 'Max').
        :param score_type: String for candidate selection strategy. 'MLI' or 'MEI'
        :param wait_time: Wait time in seconds (int) before polling API.
        :param sampler: What type of sampling to use for design.
            ['Default' or 'This view']
        :param print_output: Boolean flag for whether or not to print outputs.
        :return: An SL_run object.
        '''

        # Attributes from arguments
        self.client = client
        self.view_id = view_id
        self.dataset_id = dataset_id
        self.orig_dataset_id = orig_dataset_id
        self.target = target
        self.score_type = score_type
        self.wait_time = wait_time
        self.sampler = sampler
        self.print_output = print_output
        self.y_col = self.target[0].replace('Property ','')

        # Empty attributes to add onto later
        self.curr_iter = 0
        self.curr_design_id = None
        self.measurements = pd.DataFrame(columns=all_dataset_cols)
        self.candidates = pd.DataFrame()

        # Dataset should have training data (iteration "0")
        # Stick this in the measurements DataFrame as iter 0
        query_dataset = \
            PifSystemReturningQuery(size=9999,
                query=DataQuery(
                    dataset=DatasetQuery(
                        id=Filter(equal=str(self.dataset_id))),
                    system=PifSystemQuery(
                        properties=PropertyQuery(
                            name=FieldQuery(filter=Filter(equal=self.y_col)),
                            value=FieldQuery(filter=Filter(exists=True))
                        )
                    )
                )
            )
        query_result = self.client.search.pif_search(query_dataset)
        training_measurements = query_results_to_df(query_result)
        training_measurements['iter'] = 0
        self.measurements = pd.concat([self.measurements, training_measurements],
                                      sort=True)
        self.measurements['iter'] = self.measurements['iter'].astype(int)
        self.last_op = 'measure'


    def _wait_on_ingest(self):
        '''
        Utility function to check for data ingest completion.

        :return: None.
        '''

        sleep(self.wait_time)
        while (self.client.data.get_ingest_status(self.dataset_id) != "Finished"):
            if self.print_output:
                print("Waiting for data ingest to complete...")
            sleep(self.wait_time)
        print("Ingest finished.")
        sleep(2)


    def _wait_on_data_view(self):
        '''
        Utility function to check for data view creation completion.

        :return: None.
        '''

        sleep(self.wait_time)
        while True:
            design_status = self.client.data_views.get_data_view_service_status(self.view_id)
            if (design_status.experimental_design.ready and
                design_status.predict.event.normalized_progress == 1.0):
                if self.print_output:
                    print("Design ready.")
                break
            else:
                print("Waiting for design services...")
        sleep(2)


    def _wait_on_design_run(self, design_id):
        '''
        Utility function to check for design run completion.

        :param design_id: Integer ID of the submitted design run.
        :return: None.
        '''

        sleep(self.wait_time)
        while True:
            status = self.client.models.get_design_run_status(self.view_id, design_id).status
            if self.print_output:
                print("Design run status: {}.".format(status))
            if status != "Finished":
                sleep(self.wait_time)
            else:
                break
        sleep(2)


    def _get_valid_candidates(self, num_candidates = 1, num_seeds = 20,
                              design_effort = 5):
        '''
        Wrapper function for design runs that ensures we get back valid
        candidates with non-zero uncertainty.

        :param num_candidates: The number of candidates to return.
        :param num_seeds: The number of candidates to request from Design.
        :param design_effort: The effort for Design runs.
        :return valid_candidates: A list of material candidates from Design.
        '''

        valid_candidates = []
        while len(valid_candidates)<num_candidates:
            # Submit a design run
            design_id = self.client.models.submit_design_run(
                data_view_id=self.view_id,
                num_candidates=num_seeds,
                effort=design_effort,
                target=Target(*self.target),
                constraints=[],
                sampler=self.sampler
            ).uuid

            if self.print_output:
                print("Created design run with ID {}.".format(design_id))

            # Wait for design to complete
            self._wait_on_design_run(design_id)

            # Get candidates
            if self.score_type == "MEI":
                candidates = \
                    self.client.models.get_design_run_results(self.view_id,
                                                    design_id).best_materials
            else:
                candidates = \
                    self.client.models.get_design_run_results(self.view_id,
                                                    design_id).next_experiments

            # Remove zero-uncertainty candidates
            candidates_filtered = \
                [c for c in candidates if
                    float(c['descriptor_values']['Uncertainty in {}'.format(self.target[0])])>1e-6]
            valid_candidates.extend(candidates_filtered)
            [vc.update(design_id=design_id) for vc in valid_candidates]

            if self.print_output:
                print("{} candidates obtained.".format(num_candidates))

        return valid_candidates


    def design(self, num_candidates = 1, design_effort = 5):
        '''
        Submit a design run, get candidates, and add them to self.candidates.

        :param num_candidates: Integer number of candidates to return for this run.
        :param design_effort: Effort as an integer from 1 to 30.
        :return: None.
        '''

        if self.last_op=='design':
            raise Exception('Design was already run for this iteration')
        self.curr_iter += 1

        # Ensure ingest and view creation are complete
        self._wait_on_ingest()
        self._wait_on_data_view()

        # Get candidates (wrapper for submit_design_run)
        candidates = self._get_valid_candidates(num_candidates=num_candidates,
                                                design_effort=design_effort)

        # Candidate DataFrame
        df_cand = candidates_to_df(candidates)
        df_cand['iter'] = self.curr_iter
        df_cand['design_effort'] = design_effort
        df_cand = df_cand.sort_values('citrine_score', ascending=False).iloc[:num_candidates]
        self.candidates = pd.concat([self.candidates, df_cand.copy()])

        if self.print_output:
            best_val_w_uncertainty = \
                df_cand[[self.target[0],
                         'Uncertainty in '+self.target[0]]].iloc[0].values
            print("SL iter #{}, best predicted (value, uncertainty) = {}".format(
                self.curr_iter, best_val_w_uncertainty))

        self.last_op = 'design'


    def measure(self):
        '''
        Measure the true_function for the most recent batch of candidates
        and add them to self.measurements and the online dataset.

        :return: None.
        '''

        if self.last_op == 'measure':
            raise Exception('Candidates were already measured for this iteration.')
        if len(self.candidates) == 0:
            raise Exception('No candidates to measure, please run design.')

        # Get candidates DataFrame for current iteration
        curr_candidates_df = self.candidates.query("iter==@self.curr_iter")
        search_results = []

        # Search original dataset for the chosen samples
        if self.print_output:
            print("Measuring new candidates...")
        for ii,cand in curr_candidates_df.iterrows():
            cand_prop_query = [PropertyQuery(name=FieldQuery(filter=Filter(equal='Sample Number')),
                                            logic='MUST',
                                            value=FieldQuery(filter=
                                                Filter(min=cand['Property Sample Number']-0.1,
                                                       max=cand['Property Sample Number']+0.1)))]
            system_query_cand = PifSystemReturningQuery(
                size=9999,
                query=DataQuery(
                    dataset=DatasetQuery(
                        id=Filter(
                            equal=self.orig_dataset_id)),
                    system=PifSystemQuery(
                        properties=cand_prop_query,
                    )
                )
            )
            query_result_cand = self.client.search.pif_search(system_query_cand)
            search_results.append(query_result_cand.hits[0])


        # Store new measurements
        curr_measurements = query_results_to_df(search_results)
        curr_measurements['iter'] = self.curr_iter
        self.measurements = pd.concat([self.measurements,
                                       curr_measurements],
                                      sort=True)


        # Write measurements to dataset
        self.curr_design_id = curr_candidates_df["design_id"].iloc[0]
        temp_dataset_fpath = os.path.join('temp',
                                          "design-{}.json".format(self.curr_design_id))

        with open(temp_dataset_fpath, "w") as f:
            f.write(pif.dumps([h._system for h in search_results],
                              indent=4))


        # Upload results and re-train model
        upload_data_and_get_id(
            self.client,
            "", # No name needed for updating a dataset
            temp_dataset_fpath,
            given_dataset_id=self.dataset_id
        )
        self._wait_on_ingest()

        if self.print_output:
            print("Dataset updated: {} candidates added.".format(len(search_results)))
            print("New dataset contains {} PIFs.".format(len(self.measurements)))
            print('Retraining model...')

        # Re-train the model with the new data
        self.client.data_views.models.retrain(self.view_id)
        self._wait_on_data_view()

        self.last_op = 'measure'


    def plot_sl_results(self, figsize = (8,7)):
        '''
        Helper function to plot the SL results for each iteration.

        :param figsize: How large to make each rendered plot.
        :return fig: A matplotlib figure object.
        '''

        # Get best point in initial training set
        if self.target[1] == 'Min':
            init_best = self.measurements.query("iter==0")[self.y_col].min()
        else:
            init_best = self.measurements.query("iter==0")[self.y_col].max()

        df_meas = self.measurements.reset_index().copy()
        df_pred = self.candidates.reset_index().copy()

        # Data aggregation
        if self.target[1]=='Min':
            df_meas['best'] = df_meas[self.y_col].cummin()
            df_best_cum = \
                df_meas.loc[df_meas.groupby('iter')['best'].idxmin()]
            df_best_meas = \
                df_meas.loc[df_meas.groupby('iter')[self.y_col].idxmin()]
            df_best_pred = \
                df_pred.loc[df_pred.groupby('iter')[self.target[0]].idxmin()]
        else:
            df_meas['best'] = df_meas[self.y_col].cummax()
            df_best_cum = \
                df_meas.loc[df_meas.groupby('iter')['best'].idxmax()]
            df_best_meas = \
                df_meas.loc[df_meas.groupby('iter')[self.y_col].idxmax()]
            df_best_pred = \
                df_pred.loc[df_pred.groupby('iter')[self.target[0]].idxmax()]

        # Create Figure
        fig, ax = plt.subplots(1, 1, figsize=figsize, tight_layout=True)

        # Cumulative Best Measurements
        plt.sca(ax)
        plt.plot('iter',
                 'best',
                 data=df_best_cum,
                 color='xkcd:steel blue',
                 linewidth=3,
                 linestyle='-',
                 label="Best Measured Candidate (Cumulative)")

        # Best candidate in training set
        plt.plot(np.arange(0, len(df_best_pred)+1),
                 [init_best] * (len(df_best_pred)+1),
                 color='xkcd:black',
                 linestyle='--',
                 linewidth=3,
                 label="Best Initial Point",
                 alpha=0.7)

        # Candidate Predictions with Error Bars per iteration
        ax.errorbar(x='iter',
                    y=self.target[0],
                    fmt='o',
                    yerr="Uncertainty in "+self.target[0],
                    data=df_best_pred,
                    linewidth=3,
                    color="xkcd:orange",
                    label="Candidate Predictions w/ Uncertainty")

        # Candidate Measurements per iteration
        plt.plot('iter',
                self.y_col,
                's',
                data=df_best_meas,
                color='xkcd:maroon',
                label="Candidate Measurements")

        plt.xlabel("SL iteration #")
        plt.xticks(df_best_meas['iter'])
        plt.ylabel("Fatigue Strength (MPa)")
        plt.title("Optimizing using MLI")
        plt.legend(loc='best')
        plt.grid(b=False, axis='x')
        plt.show()

        return fig
