#!/usr/bin/env python3

"""
    create-protocol.py

    Usage:
    create-protocol.py <csv_file> <json_file> <python_file> <output_file>

    Input:
    <csv_file>       Path to the CSV file containing experiment data.
    <json_file>      Path to the JSON file containing protocol parameters.
    <python_file>    Path to the Python template of the specified protocol.
    <output_file>    Path to the output Python protocol with added data.

"""

from docopt import docopt
from typing import Any, NoReturn

def read_csv(csv_filename: str) -> str:
    """
    Reads the entire contents of a CSV file and returns it as a string.
    """
    with open(csv_filename, "r") as csv_file:
        return csv_file.read()

def read_json(json_filename: str) -> str:
    """
    Reads the entire contents of a JSON file and returns it as a string.
    """
    with open(json_filename, "r") as json_file:
        return json_file.read()

def add_data_to_template(csv_filename: str, json_filename: str, python_filename: str, output_filename: str) -> NoReturn:
    """
    Reads data from CSV and JSON files and adds it to a Python template, then writes the result to an output file.
    """
    with open(python_filename, "r") as python_file:
        original_content = python_file.read()
    csv_content = read_csv(csv_filename)
    json_content = read_json(json_filename)
    
    with open(output_filename, "w") as output_file:
        output_file.write(f'csv_data = """{csv_content}"""\n\n')
        output_file.write(f'json_parameters = """{json_content}"""\n\n{original_content}')


def main():
    """
    Main function that processes command line arguments and calls the function to add data to the template.
    """
    args = docopt(__doc__)
    csv_data = args["<csv_file>"]
    json_data = args["<json_file>"]
    protocol_template = args["<python_file>"]
    protocol_output = args["<output_file>"]

    add_data_to_template(csv_data, json_data, protocol_template, protocol_output)

if __name__ == "__main__":
    main()
