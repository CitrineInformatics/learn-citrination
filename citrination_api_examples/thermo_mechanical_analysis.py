from __future__ import print_function
import re, os, sys, argparse
import numpy as np
from scipy import stats
from math import *
#import plotly.plotly as py
#import plotly.graph_objs as go
__author__ = 'saurabh'


def get_options():
    """ standard get terminal options/flags """
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory",
                        help="specify directory of relevent documents",
                        dest="txt_file_dir",default=None)
    parser.add_argument("-f", "--file",
                        help="specify the data file location",
                        dest="txt_file_path",default=None)
    parser.add_argument("-o", "--out_directory",
                        help="specify the data output location",
                        dest="out_dir", default=os.getcwd())
    parser.add_argument("-gzip", help="gzip the output",
                        dest="gzip_bool",action="store_true")
    parser.add_argument("-ho", help="HTML out file path",
                        dest="html_file_path_out", default=None)

    options = parser.parse_args()
    try: # check that both options are not blank
        assert (options.txt_file_dir is None and options.txt_file_path is not None)\
            or (options.txt_file_dir is not None and options.txt_file_path is None), "!"
    except AssertionError:
        sys.stderr.write("invalid inputs for -f or -d \nDSC_parser.py -h for more help\n")
        exit(1)

    return options


def plot_graphs(list1, list2, graph_title, x_title, y_title):
    """
        DESCRIPTION: This function plots the plotly graphs and generates the link to the graph
        INPUTS  : list1 - x axis data
                  list2 - y axis data
                  graphTitle - Title of the graph
                  xAxisTitle - Label for x-axis
                  yAxisTitie - Label of y-axis
        OUTPUTS : link to plotly graph
        DEPENDENCIES: (extract_data()) lists of data for axes
    """
    trace = go.Scatter(
        x=list1,
        y=list2,
        name='Trace'
    )
    data = [trace]

    layout = go.Layout(
        title=graph_title,
        shapes=[
            dict(
                type='line',
                x0=list1[1],
                y0=list2[1],
                x1=list1[6],
                y1=list2[6],
                opacity=0.7,
                line=dict(
                    color='red',
                    width=2.5
                ),
            )],
        xaxis=dict(
            title=x_title
        ),
        yaxis=dict(
            title=y_title
        ), showlegend=True, legend=dict(
            x=1,
            y=1
        )
    )
    fig = go.Figure(data=data, layout=layout)
    return py.plot(fig, filename=graph_title, auto_open=False)


def smooth_spline(y, window_size, order, deriv=0, rate=1):
    """
        DESCRIPTION: This function applies the savitzky golay algorithm
                     for smoothing out the data points of the cycle
        INPUTS  : y - list of data elements
                  window_size - size of filter window i.e, coefficients
                  order - the order of polynomial equation of the fit line
                  deriv - order of the derivative
                  rate: spacing of the samples for which the filtering is applied
        OUTPUTS : numPy array of filtered points forming the smoother curve
    """
    window_size = np.abs(np.int(window_size))
    order = np.abs(np.int(order))
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order + 1)
    half_window = (window_size - 1) // 2
    # precompute coefficients
    b = np.mat([[k ** i for i in order_range] for k in range(-half_window, half_window + 1)])
    m = np.linalg.pinv(b).A[deriv] * rate ** deriv * factorial(deriv)
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - np.abs(y[1:half_window + 1][::-1] - y[0])
    lastvals = y[-1] + np.abs(y[-half_window - 1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    return np.convolve(m[::-1], y, mode='valid')


class Thermo:
    def __init__(self, file):
        """
            DESCRIPTION: This function initializes the various class variables
                         required for data and value retention
            INPUTS  : file - file path
            OUTPUTS : N/A
            DEPENDENCIES : N/A
        """
        self.displacement, self.force, self.strain, self.stress = [], [], [], []
        self.file = file
        self.elastic_modulus = None
        self.critical_stress = None

    def extract_data(self):
        """
            DESCRIPTION: The function extracts data based on pattern matching
                         with the raw data file and create various lists based
                         on further data processing requirements
            INPUTS  : N/A
            OUTPUTS : N/A
            DEPENDENCIES : txt
        """
        regex = "([-+]?\d*\.\d+)\s([-+]?\d*\.\d+)\s([-+]?\d*\.\d+)\s([-+]?\d*\.\d+)"

        with open(self.file, 'r+') as f:
            for line in f.readlines():
                data = re.match(regex, line)
                
                if data is not None:
                    self.displacement.append(float(data.group(1)))
                    self.force.append(float(data.group(2)))
                    self.strain.append(float(data.group(3)))
                    self.stress.append(float(data.group(2))/3)

    def generate_html(self, html_file):
        """
            DESCRIPTION: This function generates the HTML file by embedding the plotly links
                         and calculated variables in the string which represent the entire HTML page
            INPUTS  : html_file - html file path
            OUTPUTS : HTML file
            DEPENDENCIES : (extract_data() & calc_elastic_modulus) links to plotly graphs
                            and elastic modulus & critical stress values
        """
        fd_plot = plot_graphs(list1=self.displacement, list2=self.force,
                              graph_title='Force vs Displacement', x_title='Displacement', y_title='Force')
        ss_plot = plot_graphs(list1=self.strain, list2=self.stress,
                              graph_title='Stress vs Strain', x_title='Strain', y_title='Stress')

        html_string = '''
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <meta charset="UTF-8">
                    <title>Thermo Mechanical Analysis</title>
                </head>
                <body style="margin-left: 21%; font-family: 'Helvetica'" >
                    <div class="header">
                        <h1 style="margin-top:25px;" >Thermo Mechanical Analysis</h1>
                        <p style="margin-top: 10px">This is an HTML file for the Thermo-Mechanical data. Please feel free to hover the mouse on the curves to get more info on the DSC curves</p>
                        <hr width="80%" align="left">
                        <div class="container">
                            <h3 style="margin-top:50px">Force vs Displacement</h3>
                            <p style="margin-top: 10px">The chart depicting force vs displacement of material is plotted here.</p>
                            <div style="margin:0 auto 50 auto">
                                <iframe width="600" height="350" frameborder="0" seamless="seamless" scrolling="no"
                                src="{0}.embed?width=600&height=350"></iframe>
                            </div>
                        </div>
                        <hr width="80%" align="left">
                        <div class="container">
                            <h3 style="margin-top:50px">Stress vs Strain</h3>
                            <p style="margin-top: 10px">The chart of Stress v/s Strain is plotted here.</p>
                            <div style="margin:0 auto 50 auto">
                                <iframe width="600" height="350" frameborder="0" seamless="seamless" scrolling="no"
                                src="{1}.embed?width=600&height=350"></iframe>
                            </div>
                        </div>
                        </br>
                        <h4>Elastic Modulus of the curve: {2:.2f}</h4>
                        </br>
                        <h4>Critical Stress for the material: {3:.2f}</h4>
                    </div>
                </body>
                </html>'''.format(fd_plot, ss_plot, self.elastic_modulus, self.critical_stress)

        file = open(html_file, "w")
        file.write(html_string)
        file.close()

    def calc_elastic_modulus(self):
        """
            DESCRIPTION: The function calculates values of elastic modulus
                         and critical stress based on the extracted data lists
            INPUTS  : N/A
            OUTPUTS : N/A
            DEPENDENCEIES : extract_data() data lists for stress and strain
        """
        data_quadrant = int(len(self.strain)/10)

        self.strain = smooth_spline(np.array(self.strain), 51, 3).tolist()

        x = np.array(self.strain[data_quadrant*2:data_quadrant*3])
        y = np.array(self.stress[data_quadrant*2:data_quadrant*3])

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        self.elastic_modulus = slope
        print("Elastic Modulus:" + str(self.elastic_modulus))

        prev_stress, curr_stress = 0, 1
        cntr = data_quadrant * 3
        while prev_stress < curr_stress:
            prev_stress = self.stress[cntr] * 1.002
            cntr += 4
            curr_stress = self.stress[cntr]

        self.critical_stress = prev_stress
        print("Critical Stress:" + str(self.critical_stress))


def main():
    """
        DESCRIPTION: The function acts as the primary controller
                     for handlng multiple files.
                     It spawns new objects for each experiment file.
    """
    options = get_options()
    experiment = Thermo(file=options.txt_file_path)
    experiment.extract_data()
    experiment.calc_elastic_modulus()
    #experiment.generate_html(html_file=options.html_file_path_out)

if __name__ == '__main__':
    """
        Main block of code for workflow
    """
    main()