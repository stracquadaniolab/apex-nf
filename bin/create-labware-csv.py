#!/usr/bin/env python3

"""
    create_csv_labware.py

    Usage:
    create_csv_labware.py <csv_file> <json_file> <output_file>

    Input:
    <csv_file>       Path to the CSV file containing experiment data.
    <json_file>      Path to the JSON file containing protocol parameters.
    <output_file>    Path to the output csv file with labware data.
"""

import pandas as pd
import json
from docopt import docopt

def create_transformation_labware(data_csv, parameters_json, output_csv):

    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as f:
        plate_slots = json.load(f)

    df_all_reactants = []
    for reactant in ['dna', 'cells', 'media']:

        well_col = f'{reactant}_well'
        volume_col = f'{reactant}_volume'
        id_col = f'{reactant}_ID'

        df_id_well_volume = df.groupby(well_col).agg({volume_col: 'sum', id_col: 'first'}).reset_index() # sum the volumes of reactants
        df_id_well_volume.rename(columns={id_col: 'ID', well_col: 'well_name', volume_col: 'volume'}, inplace=True)
        df_id_well_volume["location"] = plate_slots[f'{reactant}_plate_slot']
        df_id_well_volume["labware"] = plate_slots[f'{reactant}_plate_name']

        df_all_reactants.append(df_id_well_volume) 

    # transformation dataframe
    df_transformation = pd.DataFrame({
        'ID': df.apply(lambda row: f"{row['dna_ID']}/{row['cells_ID']}/{row['media_ID']}", axis=1),
        'well_name': df['transformation_well'],
        'volume': df[['dna_volume', 'cells_volume', 'media_volume']].sum(axis=1),
        "labware": plate_slots['transformation_plate_name'],
        'location': 'thermocycler'
    })
    df_all_reactants.append(df_transformation) 

    result_df = pd.concat(df_all_reactants, ignore_index=True) # Concatenate the grouped dataframes vertically
    result_df = result_df.reindex(columns=['ID', 'location', 'labware', 'well_name', 'volume']) # Reorder columns
    result_df.to_csv(output_csv, index=False) # write to a CSV file


def create_spotting_labware(data_csv, parameters_json, output_csv):
    """
    This function creates a csv file from spotting CSV and JSON files for the labware visualisation.
    """

    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as f:
        plate_slots = json.load(f)

    df.rename(columns={"location": "location", "destination_well": "well_name", "spotting_volume": "volume"}, inplace=True) # Rename columns
    df = df[["ID", "location", "well_name", "volume"]]
    df["labware"] = plate_slots['agar_plate_name']
    df = df.reindex(columns=['ID', 'location', 'labware', 'well_name', 'volume']) # Reorder columns
    df.to_csv(output_csv, index=False) # Write to a CSV file

def main():
    args = docopt(__doc__)
    csv_data = args['<csv_file>']
    json_data = args['<json_file>']
    csv_output = args['<output_file>']

    if "transformation" in csv_data:
        create_transformation_labware(csv_data, json_data, csv_output)
    elif "spotting":
        create_spotting_labware(csv_data, json_data, csv_output)
    else:
        print("Invalid experiment name.")

if __name__ == "__main__":
    main()
