'''
Authors: Eddie Kim, Enze Chen
This file contains wrapper functions that are used in the sequential learning API tutorial notebook. Detailed docstrings with method fuctions and parameters are given below.
'''

import json
from collections import OrderedDict
from time import sleep

import numpy as np
import matplotlib.pyplot as plt
from citrination_client import (CitrinationClient, DataQuery, DatasetQuery,
                                Filter, PifSystemReturningQuery,
                                RealDescriptor)
from citrination_client.models.design import Target
from citrination_client.views.data_view_builder import DataViewBuilder
from pypif import pif
from pypif.obj import *


def write_dataset_from_func(test_function, filename, input_vals):
    '''Given a function, write a dataset evaluated on given input values

    :param test_function: Function for generating dataset
    :type test_function: Callable[[np.ndarray], float]
    :param filename: Name of file for saving CSV dataset
    :type filename: str
    :param input_vals: List of input values to eval function over
    :type input_vals: np.ndarray
    :return: Doesn't return anything
    :rtype: None
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
        func_output.name = 'y'
        func_output.scalars = test_function(val_row)
        system.properties.append(func_output)
        pif_systems.append(system)

    with open(filename, "w") as f:
        f.write(pif.dumps(pif_systems, indent=4))


def upload_data_and_get_id(client, dataset_name, dataset_local_fpath,
                        create_new_version = False, given_dataset_id = None):
    '''Uploads data to a new/given dataset and returns its ID

    :param client: Client API object to pass in
    :type client: CitrinationClient
    :param dataset_name: Name of dataset
    :type dataset_name: str
    :param dataset_local_fpath: Local data filepath
    :type dataset_local_fpath: str
    :param create_new_version: Whether or not to make a new version
    :param create_new_version: bool
    :param given_dataset_id: ID if using existing dataset, defaults to None
    :param given_dataset_id: int
    :return: ID of the dataset
    :rtype: int
    '''

    if given_dataset_id is None:
        dataset = client.data.create_dataset(dataset_name)
        dataset_id = dataset.id
    else:
        dataset_id = given_dataset_id
        if create_new_version:
            client.data.create_dataset_version(dataset_id)

    client.data.upload(dataset_id, dataset_local_fpath)
    assert (client.data.matched_file_count(dataset_id) >= 1), "Upload failed."
    return dataset_id


def build_view_and_get_id(client, dataset_id, input_keys, output_keys, view_name, view_desc = "",
                        wait_time = 2, print_output = False):
    '''Builds a new data view and returns the view ID

    :param client: Client object
    :type client: CitrinationClient
    :param dataset_id: Dataset to build view from
    :type dataset_id: int
    :param view_name: Name of the new view
    :type view_name: str
    :param input_keys: Input key names
    :type input_keys: List[str]
    :param output_keys: Output key names
    :type output_keys: List[str]
    :param view_desc: Description for the view, defaults to ""
    :param view_desc: str, optional
    :param wait_time: Wait time in seconds before polling API
    :type wait_time: int
    :param print_output: Whether or not to print outputs
    :type print_output: bool
    :return: ID of the view
    :rtype: int
    '''

    dv_builder = DataViewBuilder()
    dv_builder.dataset_ids([str(dataset_id)])
    dv_builder.model_type('default')

    for key_name in input_keys:
        desc_x = RealDescriptor(key=key_name, lower_bound=-1e6, upper_bound=1e6)
        dv_builder.add_descriptor(desc_x, role='input')

    for key_name in output_keys:
        desc_y = RealDescriptor(key=key_name, lower_bound=-1e6, upper_bound=1e6)
        dv_builder.add_descriptor(desc_y, role='output')

    dv_config = dv_builder.build()

    _wait_on_ingest(client, dataset_id, wait_time, print_output)

    dv_id = client.data_views.create(
        configuration=dv_config,
        name=view_name,
        description=view_desc
    )
    return dv_id


def run_sequential_learning(client, view_id, dataset_id,
                        num_candidates_per_iter,
                        design_effort, wait_time,
                        num_sl_iterations, input_properties,
                        target, print_output,
                        true_function,
                        score_type):
    '''Runs SL design

    :param client: Client object
    :type client: CitrinationClient
    :param view_id: View ID
    :type view_id: int
    :param dataset_id: Dataset ID
    :type dataset_id: int
    :param num_candidates_per_iter: Candidates in a batch
    :type num_candidates_per_iter: int
    :param design_effort: Effort from 1-30
    :type design_effort: int
    :param wait_time: Wait time in seconds before polling API
    :type wait_time: int
    :param num_sl_iterations: SL iterations to run
    :type num_sl_iterations: int
    :param input_properties: Inputs
    :type input_properties: List[str]
    :param target: ("Output property", {"Min", "Max"})
    :type target: List[str]
    :param print_output: Whether or not to print outputs
    :type print_output: bool
    :param true_function: Actual function for evaluating measured/true values
    :type true_function: Callable[[np.ndarray], float]
    :param score_type: MLI or MEI
    :type score_type: str
    :return: 2-tuple: list of predicted scores/uncertainties; list of measured scores/uncertainties
    :rtype: Tuple[List[float], List[float]]
    '''



    best_sl_pred_vals = []
    best_sl_measured_vals = []

    _wait_on_ingest(client, dataset_id, wait_time, print_output)

    for i in range(num_sl_iterations):
        if print_output:
            print("\n---STARTING SL ITERATION #{}---".format(i+1))

        _wait_on_ingest(client, dataset_id, wait_time, print_output)
        _wait_on_data_view(client, dataset_id, view_id, wait_time, print_output)

        # Submit a design run
        design_id = client.models.submit_design_run(
                data_view_id=view_id,
                num_candidates=num_candidates_per_iter,
                effort=design_effort,
                target=Target(*target),
                constraints=[],
                sampler="Default"
            ).uuid

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
        _wait_on_data_view(client, dataset_id, view_id, wait_time, print_output)

    if print_output:
        print("SL finished!\n")

    return (best_sl_pred_vals, best_sl_measured_vals)


def _wait_on_ingest(client, dataset_id, wait_time, print_output = True):
    # Wait for ingest to finish
    sleep(wait_time)
    while (client.data.get_ingest_status(dataset_id) != "Finished"):
        if print_output:
            print("Waiting for data ingest to complete...")
        sleep(wait_time)


def _wait_on_data_view(client, dataset_id, view_id, wait_time, print_output = True):
    is_view_ready = False
    sleep(wait_time)
    while (not is_view_ready):
        sleep(wait_time)
        design_status = client.data_views.get_data_view_service_status(view_id)
        if (design_status.experimental_design.ready and
        design_status.predict.event.normalized_progress == 1.0):
            is_view_ready = True
            if print_output:
                print("Design ready")
        else:
            print("Waiting for design services...")


def _wait_on_design_run(client, design_id, view_id, wait_time, print_output = True):
    design_processing = True
    sleep(wait_time)
    while design_processing:
        status = client.models.get_design_run_status(view_id, design_id).status
        if print_output:
            print("Design run status: {}".format(status))

        if status != "Finished":
            sleep(wait_time)
        else:
            design_processing = False
            

def plot_sl_results(measured, predicted, init_best):
#     plt.rcParams.update({'figure.figsize':(8, 6), 'font.size':18})

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
