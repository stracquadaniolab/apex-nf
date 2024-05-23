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

# def create_induction_labware(data_csv, parameters_json, output_csv):
#     """
#     This function creates a csv file from induction CSV and JSON files for the labware visualisation.
#     """
#     df = pd.read_csv(data_csv)
#     with open(parameters_json, "r") as f:
#         plate_slots = json.load(f)

#     df_all_reactants = []
#     for reactant in ["blank", "culture", "inducer"]:

#         well_col = f"{reactant}_well"
#         volume_col = f"{reactant}_volume"
#         id_col = f"ID"

#         df_id_well_volume = df.groupby(well_col).agg({volume_col: "sum", id_col: "first"}).reset_index() # sum the volumes of reactants
#         df_id_well_volume.rename(columns={id_col: "ID", well_col: "well_name", volume_col: "volume"}, inplace=True)
#         df_id_well_volume["location"] = plate_slots[f"{reactant}_plate_slot"]
#         df_id_well_volume["labware"] = plate_slots[f"{reactant}_plate_name"]

#         df_all_reactants.append(df_id_well_volume) 

#     # Map these IDs to rows where both culture_volume and inducer_volume > 0
#     def map_ids(row):
#         if row["culture_volume"] > 0 and row["inducer_volume"] > 0:
#             # Find the matching "ID" from the "culture_only_ids" series
#             culture_id = df.loc[(df["culture_well"] == row["culture_well"]) & (df["inducer_volume"] == 0), "ID"]
#             if not culture_id.empty:
#                 return row["ID"] + "+" + culture_id.iloc[0]
#         return row["ID"]

#     df["combined_ID"] = df.apply(map_ids, axis=1)

#     # induction dataframe
#     df_induction = pd.DataFrame({
#         "ID": df["combined_ID"],
#         "well_name": df["destination_well"],
#         "volume": df[["blank_volume", "culture_volume", "inducer_volume"]].sum(axis=1),
#         "labware": plate_slots["destination_plate_name"],
#         "location": plate_slots["destination_plate_slot"]
#     })
    
    
#     df_all_reactants.append(df_induction) 

#     result_df = pd.concat(df_all_reactants, ignore_index=True) # Concatenate the grouped dataframes vertically
#     result_df = result_df.reindex(columns=["ID", "location", "labware", "well_name", "volume"]) # Reorder columns
#     result_df.to_csv(output_csv, index=False) # write to a CSV file

# def create_transfer_labware(data_csv, parameters_json, output_csv):
#     """
#     This function creates a csv file from transfer CSV and JSON files for the labware visualisation.
#     """

#     df = pd.read_csv(data_csv)
#     with open(parameters_json, "r") as f:
#         plate_slots = json.load(f)

#     # Create the source plate dataframe
#     df_source_plate = pd.DataFrame({
#         "id": df["source_id"],
#         "well_name": df["source_well"],
#         "volume": df["source_volume"],
#         "labware": plate_slots["source_plate_name"],
#         "location": plate_slots["source_plate_slot"]
#     })

#     # Create the destination plate dataframe with combined "ID"
#     df["combined_id"] = df["source_id"].astype(str) + "-" + df["destination_id"].astype(str) # Combine IDs
#     df_destination_plate = pd.DataFrame({
#         "id": df["combined_id"],
#         "well_name": df["destination_well"],
#         "volume": df["source_volume"] + df["destination_volume"],  # Adjust volume as required
#         "labware": plate_slots["destination_plate_name"],
#         "location": plate_slots["destination_plate_slot"]
#     })

#     # Concatenate the dataframes and reorder columns for the final output
#     result_df = pd.concat([df_source_plate, df_destination_plate], ignore_index=True)
#     result_df = result_df[["id", "location", "labware", "well_name", "volume"]]  # Reorder columns for consistency

#     # Write the result to a CSV file
#     result_df.to_csv(output_csv, index=False)

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
    #     create_picking_labware(csv_data, json_data, csv_output)
    # elif "induction" in csv_data:
    #     create_induction_labware(csv_data, json_data, csv_output)
    # elif "transfer" in csv_data:
    #     create_transfer_labware(csv_data, json_data, csv_output)
    # else:
    #     print("Invalid experiment name.")

if __name__ == "__main__":
    main()
