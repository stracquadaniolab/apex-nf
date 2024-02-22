#!/usr/bin/env python

"""protocol-compiler.py 

    Build a protocol for the Opentrons OT2 using a template file, json params, and CSV file.

    Usage:
        protocol-compiler.py [-d --template-dir <template_dir>] [-o --output-file <out_file>] <template_file> <json_file> <csv_file>

    Options:
    -d, --template-dir            Directory containing protocol templates [default: templates/]
    -o, --output-file             Output file [default: compiled_protocol.py].
    -h --help                     Show this screen.
    --version                     Show version.
"""


from docopt import docopt
from jinja2 import Environment, FileSystemLoader

if __name__ == "__main__":
    # parse commad line arguments
    arguments = docopt(__doc__, version="plots")

    # loading templates
    environment = Environment(loader=FileSystemLoader(arguments["<template_dir>"]))
    template = environment.get_template(arguments["<template_file>"])

    # read files directly in memory
    json_file = open(arguments["<json_file>"]).read()
    csv_file = open(arguments["<csv_file>"]).read()

    # render customized template
    content = template.render(INPUT_JSON_FILE=json_file, INPUT_CSV_FILE=csv_file)

    # save template to file
    with open(arguments["<out_file>"], mode="w", encoding="utf-8") as compiled_protocol:
        compiled_protocol.write(content)
