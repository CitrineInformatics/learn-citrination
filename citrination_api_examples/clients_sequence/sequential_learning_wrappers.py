'''
Authors: Eddie Kim, Enze Chen
This file contains wrapper functions that are used in the sequential learning
API tutorial notebook. Detailed docstrings with method fuctions and parameters
are given below.
'''

# Standard packages
import os
from time import sleep

# Third-party packages
import numpy as np
import matplotlib.pyplot as plt

# Citrine packages
from citrination_client import *
from citrination_client.models.design import Target
from citrination_client.views.data_view_builder import DataViewBuilder
from pypif import pif
from pypif.obj import *


def write_dataset_from_func(test_function, filename, input_vals):
    '''
    Given a function, write a dataset evaluated on given input values.

    :param test_function: Function for generating dataset.
    :param filename: Name of file as a string for saving CSV dataset.
    :param input_vals: List of input values as numpy array to evaluate function over.
    :return: None.
    '''

    pif_systems = []
    for i, val_row in enumerate(input_vals):
        system = System()
        system.names = '{}_{}'.format(test_function.__name__, i)
        system.properties =  []

        for j, x_val in enumerate(val_row):
            func_input = Property()
            func_input.name = 'x{}'.format(j+1)
            func_input.scalars = x_val
            system.properties.append(func_input)

        func_output = Property()
        func_output.name = 'Band gap difference'
        func_output.scalars = test_function(val_row)
        system.properties.append(func_output)
        pif_systems.append(system)

    if not os.path.exists('temp'):
        os.makedirs('temp')

    with open(os.path.join('temp', filename), "w") as f:
        f.write(pif.dumps(pif_systems, indent=4))
        print('"{}" file successfully created.'.format(filename))


def upload_data_and_get_id(client, dataset_name, dataset_local_fpath,
                           create_new_version = False, given_dataset_id = None):
    '''
    Uploads data to a new/given dataset and returns its ID.

    :param client: CitrinationClient API object to pass in.
    :param dataset_name: Name of dataset as a string.
    :param dataset_local_fpath: Local data filepath as a string.
    :param create_new_version: Boolean flag for whether or not to make a new version.
    :param given_dataset_id: Integer ID if using existing dataset; default = None.
    :return dataset_id: Integer ID of the dataset.
    '''

    if given_dataset_id is None:
        dataset = client.data.create_dataset(dataset_name)
        dataset_id = dataset.id
    else:
        dataset_id = given_dataset_id
        if create_new_version:
            client.data.create_dataset_version(dataset_id)

    client.data.upload(dataset_id, os.path.join('temp', dataset_local_fpath))
    assert (client.data.matched_file_count(dataset_id) >= 1), "Upload failed."
    return dataset_id


def build_view_and_get_id(client, dataset_id, input_keys, output_keys, view_name,
                          view_desc = '', wait_time = 2, print_output = False):
    '''
    Builds a new data view and returns the view ID.

    :param client: CitrinationClient object.
    :param dataset_id: Integer ID of the dataset to build data view from.
    :param view_name: Name of the new data view as a string.
    :param input_keys: List of string representing input key names.
    :param output_keys: List of string representing output key names.
    :param view_desc: String description for the data view.
    :param wait_time: Wait time in seconds (int) before polling API.
    :param print_output: Boolean flag for whether or not to print outputs.
    :return dv_id: Integer ID of the data view.
    '''

    dv_builder = DataViewBuilder()
    dv_builder.dataset_ids([str(dataset_id)])

    for key_name in input_keys:
        desc_x = RealDescriptor(key=key_name, lower_bound=-1e3, upper_bound=1e3)
        dv_builder.add_descriptor(descriptor=desc_x, role='input')

    for key_name in output_keys:
        desc_y = RealDescriptor(key=key_name, lower_bound=0, upper_bound=1e2)
        dv_builder.add_descriptor(descriptor=desc_y, role='output')

    dv_config = dv_builder.build()

    _wait_on_ingest(client, dataset_id, wait_time, print_output)

    dv_id = client.data_views.create(
        configuration=dv_config,
        name=view_name,
        description=view_desc)

    return dv_id


def run_sequential_learning(client, view_id, dataset_id, num_candidates_per_iter,
                            design_effort, wait_time, num_sl_iterations,
                            input_properties, target, print_output, true_function,
                            score_type):
    '''
    Runs SL design.

    :param client: CitrinationClient object.
    :param view_id: Integer ID for the data view.
    :param dataset_id: Integer ID for the data set.
    :param num_candidates_per_iter: Integer number of candidates in a batch.
    :param design_effort: Integer from 1 to 30 representing design effort.
    :param wait_time: Wait time in seconds (int) before polling API.
    :param num_sl_iterations: Integer number of SL iterations to run.
    :param input_properties: List of strings representing input property keys.
    :param target: List of strings for target property key and optimization goal.
    :param print_output: Boolean flag for whether or not to print outputs.
    :param true_function: Actual function for evaluating measured/true values.
    :param score_type: String for candidate selection strategy: 'MLI' or 'MEI'.
    :return: 2-tuple: (List of floats for predicted scores/uncertainties,
                       List of floats for measured scores/uncertainties)
    '''

    best_sl_pred_vals = []
    best_sl_measured_vals = []

    _wait_on_ingest(client, dataset_id, wait_time, print_output)

    for i in range(num_sl_iterations):
        if print_output:
            print("\n---STARTING SL ITERATION #{}---".format(i+1))

        _wait_on_ingest(client, dataset_id, wait_time, print_output)
        _wait_on_data_view(client, view_id, wait_time, print_output)

        # Submit a design run
        design_id = client.models.submit_design_run(
                data_view_id=view_id,
                num_candidates=num_candidates_per_iter,
                effort=design_effort,
                target=Target(*target),
                constraints=[]).uuid

        if print_output:
            print("Created design run with ID {}".format(design_id))

        _wait_on_design_run(client, design_id, view_id, wait_time, print_output)

        # Compute the best values with uncertainties as a list of (value, uncertainty)
        if score_type == "MEI":
            candidates = client.models.get_design_run_results(view_id, design_id).best_materials
        else:
            candidates = client.models.get_design_run_results(view_id, design_id).next_experiments
        values_w_uncertainties = [
            (
                m["descriptor_values"][target[0]],
                m["descriptor_values"]["Uncertainty in {}".format(target[0])]
            ) for m in candidates
        ]

        # Find and save the best predicted value
        if target[1] == "Min":
            best_value_w_uncertainty = min(values_w_uncertainties, key=lambda x: x[0])
        else:
            best_value_w_uncertainty = max(values_w_uncertainties, key=lambda x: x[0])

        best_sl_pred_vals.append(best_value_w_uncertainty)
        if print_output:
            print("SL iter #{}, best predicted (value, uncertainty) = {}".format(i+1, best_value_w_uncertainty))

        # Update dataset w/ new candidates
        new_x_vals = []
        for material in candidates:
            new_x_vals.append(np.array(
                [float(material["descriptor_values"][x]) for x in input_properties]
            ))

        temp_dataset_fpath = "design-{}.json".format(design_id)
        write_dataset_from_func(true_function, temp_dataset_fpath, new_x_vals)
        upload_data_and_get_id(
            client,
            "", # No name needed for updating a dataset
            temp_dataset_fpath,
            given_dataset_id=dataset_id
        )

        _wait_on_ingest(client, dataset_id, wait_time, print_output)

        if print_output:
            print("Dataset updated: {} candidates added.".format(len(new_x_vals)))

        query_dataset = PifSystemReturningQuery(size=9999,
                            query=DataQuery(
                            dataset=DatasetQuery(
                                id=Filter(equal=str(dataset_id))
                        )))
        query_result = client.search.pif_search(query_dataset)

        if print_output:
            print("New dataset contains {} PIFs.".format(query_result.total_num_hits))

        # Update measured values in new dataset
        dataset_y_values = []
        for hit in query_result.hits:
            # Assume last prop is output if following this script
            dataset_y_values.append(
                float(hit.system.properties[-1].scalars[0].value)
            )

        if target[1] == "Min":
            best_sl_measured_vals.append(min(dataset_y_values))
        else:
            best_sl_measured_vals.append(max(dataset_y_values))

        # Retrain model w/ wait times
        client.models.retrain(view_id)
        _wait_on_data_view(client, view_id, wait_time, print_output)

    if print_output:
        print("SL finished!\n")

    return (best_sl_pred_vals, best_sl_measured_vals)


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


def _wait_on_design_run(client, design_id, view_id, wait_time, print_output = True):
    '''
    Utility function to check for design run completion.

    :param client: CitrinationClient API object.
    :param design_id: Integer ID of the submitted design run.
    :param view_id: Integer ID for the data view to check.
    :param wait_time: Wait time in seconds (int) before polling API again.
    :param print_output: Boolean flag for whether to display status messages.
    :return: None.
    '''

    sleep(wait_time)
    while True:
        status = client.models.get_design_run_status(view_id, design_id).status
        if print_output:
            print("Design run status: {}.".format(status))
        if status != "Finished":
            sleep(wait_time)
        else:
            break


def plot_sl_results(measured, predicted, init_best):
    '''
    Helper function to plot the SL results for each iteration.

    :param measured: True/measured values of a property (float).
    :param predicted: Predicted values of a property (float).
    :param init_best: The best value of the property from the training set (float).
    :return: None.
    '''

    # Measured results
    plt.plot(
        np.arange(1, len(measured)+1),
        [round(float(v), 3) for v in measured],
        lw=5,
        color="#1f77b4",
        label="Measured Results"
    )

    # Predicted results
    plt.plot(
        np.arange(1, len(predicted)+1),
        [round(float(v[0]), 3) for v in predicted],
        lw=5,
        color="#ff7f0e",
        label="Predicted Results"
    )

    # Error bars
    plt.errorbar(
        x=np.arange(1, len(predicted)+1),
        y=[round(float(v[0]), 3) for v in predicted],
        yerr=[round(float(v[1]), 3) for v in predicted],
        lw=5,
        fmt='none',
        ecolor="#2ca02c",
        label="Predicted Uncertainty"
    )

    # Best candidate in training set
    plt.plot(
        np.arange(1, len(predicted)+1),
        [init_best] * len(predicted),
        label="Best in Training",
        color="black",
        lw=4,
        alpha=0.7
    )

    plt.xlabel("SL iteration #")
    plt.legend(loc='best', bbox_to_anchor=(1.25, 1.0))
    plt.ylabel("Function value")
    plt.title("Optimizing using MLI")
    plt.grid(b=False, axis='x')
    plt.show()
