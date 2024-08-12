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

def create_csv_protocol_1(data_csv: str, parameters_json: str, output_csv: str) -> None:

    """
    This function creates a CSV file from CSV and JSON files of protocol 1 compatible with the labware visualisation script.
    """
    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as file:
        plate_slots = json.load(file)

    df_all_reactants = []
    for reactant in ["dna", "cells", "media"]:
        well_col = f"{reactant}_well"
        volume_col = f"{reactant}_volume"
        id_col = f"{reactant}_id"
        df_id_well_volume = df.groupby(well_col).agg({volume_col: "sum", id_col: "first"}).reset_index() # Sum the volumes of reactants
        df_id_well_volume.rename(columns={id_col: "id", well_col: "well_name", volume_col: "volume"}, inplace=True)
        df_id_well_volume["location"] = plate_slots[f"{reactant}_plate_slot"]
        df_id_well_volume["labware"] = plate_slots[f"{reactant}_plate_name"]
        df_all_reactants.append(df_id_well_volume) 

    # Transformation plate dataframe
    df_destination = pd.DataFrame({
        "id": df.apply(lambda row: f'{row["dna_id"]}/{row["cells_id"]}/{row["media_id"]}', axis=1),
        "well_name": df["destination_well"],
        "volume": df[["dna_volume", "cells_volume", "media_volume"]].sum(axis=1),
        "labware": plate_slots["destination_plate_name"],
        "location": plate_slots["destination_plate_slot"]
    })
    df_all_reactants.append(df_destination) 
    result_df = pd.concat(df_all_reactants, ignore_index=True) # Concatenate the grouped dataframes vertically
    result_df = result_df.reindex(columns=["id", "location", "labware", "well_name", "volume"]) # Reorder columns
    result_df.to_csv(output_csv, index=False)

def create_csv_protocol_2(data_csv: str, parameters_json: str, output_csv: str) -> None:
    """
    This function creates a CSV file from spotting CSV and JSON files compatible with the labware visualisation script.
    """
    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as file:
        params = json.load(file)

    # Create the source plate dataframe
    df_source_plate = pd.DataFrame({
        "id": df["id"],
        "well_name": df["source_well"],
        "volume": df["spotting_volume"],
        "labware": params["source_plate_name"],
        "location": params["source_plate_slot"]
    })

    # Create the destination plate dataframe with a list of numbers for location
    df_destination_plate = pd.DataFrame({
        "id": df["id"],
        "well_name": df["destination_well"],
        "volume": df["spotting_volume"],
        "labware": params["agar_plate_name"],
        "location": 2
    })

    result_df = pd.concat([df_source_plate, df_destination_plate], ignore_index=True)  # Concatenate the dataframes
    result_df = result_df[["id", "location", "labware", "well_name", "volume"]]  # Reorder columns for consistency
    result_df.to_csv(output_csv, index=False)  # Write the result to a CSV file

def create_csv_protocol_3(data_csv: str, parameters_json: str, output_csv: str) -> None:
    """
    This function creates a csv file from picking CSV and JSON files for the labware visualisation.
    """

    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as file:
        plate_slots = json.load(file)

    df_all_reactants = []

    df_source_plate = pd.DataFrame({
        "id": df["id"],
        "well_name": df["sampling_source_well"],
        "volume": 0,
        "labware": plate_slots["agar_plate_name"],
        "location": 1
    })
    df_all_reactants.append(df_source_plate) 

    df_destination_plate = pd.DataFrame({
        "id": df["id"],
        "well_name": df["destination_well"],
        "volume": df["media_volume"],
        "labware": plate_slots["media_plate_name"],
        "location": plate_slots["media_plate_slot"]
    })
    df_all_reactants.append(df_destination_plate) 

    result_df = pd.concat(df_all_reactants, ignore_index=True) # Concatenate the grouped dataframes vertically
    result_df = result_df.reindex(columns=["id", "location", "labware", "well_name", "volume"]) # Reorder columns
    result_df.to_csv(output_csv, index=False) # write to a CSV file

def create_csv_protocol_4(data_csv, parameters_json, output_csv):
    """
    Creates a CSV file for labware visualization using data from CSV and JSON configuration files.
    This function aggregates lab data by wells, calculates combined IDs from multiple reactants, and outputs
    a consolidated CSV file for visualizing labware placement in protocol 4 experiments.
    """
    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as f:
        plate_slots = json.load(f)

    reactants = [key.replace('_plate_slot', '') for key in plate_slots if '_plate_slot' in key]

    df_all_reactants = []
    for reactant in reactants:
        well_col = f"{reactant}_well"
        volume_col = f"{reactant}_volume"
        id_col = f"{reactant}_id"

        if well_col in df.columns and volume_col in df.columns and id_col in df.columns:
            df_reactant = df.groupby(well_col).agg({volume_col: "sum", id_col: "first"}).reset_index()
            df_reactant.rename(columns={id_col: "id", well_col: "well_name", volume_col: "volume"}, inplace=True)
            df_reactant["location"] = plate_slots.get(f"{reactant}_plate_slot", 'Unknown')
            df_reactant["labware"] = plate_slots.get(f"{reactant}_plate_name", 'Unknown')
            
            df = df.merge(df_reactant[['well_name', 'id']], left_on=well_col, right_on='well_name', suffixes=('', f'_{reactant}'))
            df_all_reactants.append(df_reactant)

    reactant_ids = [f"{reactant}_id" for reactant in reactants if f"{reactant}_id" in df.columns]
    df['combined_id'] = df[reactant_ids].apply(lambda x: '/'.join(x.dropna().astype(str)), axis=1)

    df_induction = pd.DataFrame({
        "id": df['combined_id'],
        "well_name": df["destination_well"],
        "volume": df[[col for col in df.columns if "volume" in col and any(r in col for r in reactants)]].sum(axis=1),
        "labware": plate_slots["destination_plate_name"],
        "location": plate_slots["destination_plate_slot"]
    })
    
    df_all_reactants.append(df_induction)

    result_df = pd.concat(df_all_reactants, ignore_index=True)
    result_df = result_df.reindex(columns=["id", "location", "labware", "well_name", "volume"])
    result_df.to_csv(output_csv, index=False)
    
    df_all_reactants.append(df_induction) 

    result_df = pd.concat(df_all_reactants, ignore_index=True) # Concatenate the grouped dataframes vertically
    result_df = result_df.reindex(columns=["id", "location", "labware", "well_name", "volume"]) # Reorder columns
    result_df.to_csv(output_csv, index=False) # write to a CSV file


def main():
    args = docopt(__doc__)
    csv_data = args["<csv_file>"]
    json_data = args["<json_file>"]
    csv_output = args["<output_file>"]

    if "1" in csv_data:
        create_csv_protocol_1(csv_data, json_data, csv_output)
    elif "2" in csv_data:
        create_csv_protocol_2(csv_data, json_data, csv_output)

    elif "3" in csv_data:
        create_csv_protocol_3(csv_data, json_data, csv_output)
    
    if "4" in csv_data:
        create_csv_protocol_4(csv_data, json_data, csv_output)

if __name__ == "__main__":
    main()