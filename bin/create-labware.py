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


def process_reactant(df, reactant_config, plate_slots):
    """
    Processes a reactant to create a DataFrame with standardised columns.
    Args:
        df: Data frame with experiment data
        reactant_config: Dictionary containing reactant configuration
        plate_slots: Dictionary containing plate slot information
    """
    well_col = reactant_config.get("well_col")
    volume_col = reactant_config.get("volume_col")
    id_col = reactant_config.get("id_col")
    fixed_id = reactant_config.get("fixed_id")
    custom_df_func = reactant_config.get("custom_df_func")
    
    if custom_df_func:
        df_grouped = custom_df_func(df, reactant_config, plate_slots)
    elif well_col and volume_col:
        if id_col:
            df_grouped = df.groupby(well_col).agg({volume_col: "sum", id_col: "first"}).reset_index()
            df_grouped.rename(columns={id_col: "id", well_col: "well_name", volume_col: "volume"}, inplace=True)
        else:
            df_grouped = df.groupby(well_col)[volume_col].sum().reset_index()
            df_grouped.rename(columns={well_col: "well_name", volume_col: "volume"}, inplace=True)
            if fixed_id:
                df_grouped["id"] = fixed_id

    if "location" not in df_grouped.columns:
        df_grouped["location"] = plate_slots.get(reactant_config.get("location_key"), reactant_config.get("location_value", ""))
    if "labware" not in df_grouped.columns:
        df_grouped["labware"] = plate_slots.get(reactant_config.get("labware_key"), reactant_config.get("labware_value", ""))
    
    return df_grouped

def create_csv_protocol_1(data_csv, parameters_json, output_csv):
    """This function creates a CSV file from CSV and JSON files of protocol 1 compatible with the labware visualisation script."""
    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as file:
        plate_slots = json.load(file)

    df_all_reactants = []
    
    reactants = ["dna", "cells", "media"]
    for reactant in reactants:
        reactant_config = {
            "well_col": f"{reactant}_source_well",
            "volume_col": f"{reactant}_volume",
            "id_col": f"{reactant}_id",
            "location_key": f"{reactant}_plate_slot",
            "labware_key": f"{reactant}_plate_name"
        }
        df_reactant = process_reactant(df, reactant_config, plate_slots)
        df_all_reactants.append(df_reactant)

    def destination_df_func(df, config, plate_slots):
        return pd.DataFrame({
            "id": df.apply(lambda row: f'{row["dna_id"]}/{row["cells_id"]}/{row["media_id"]}', axis=1),
            "well_name": df["transformation_well"],
            "volume": df[["dna_volume", "cells_volume", "media_volume"]].sum(axis=1)
        })
    
    destination_config = {
        "custom_df_func": destination_df_func,
        "labware_key": "transformation_plate_name",
        "location_value": "thermocycler"
    }
    
    df_destination = process_reactant(df, destination_config, plate_slots)
    df_all_reactants.append(df_destination)
    
    result_df = pd.concat(df_all_reactants, ignore_index=True)
    result_df = result_df.reindex(columns=["id", "location", "labware", "well_name", "volume"])
    result_df.to_csv(output_csv, index=False)

def create_csv_protocol_2(data_csv, parameters_json, output_csv):
    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as file:
        params = json.load(file)

    df_all_reactants = []
    
    def source_df_func(df, config, params):
        return pd.DataFrame({
            "id": df["sample_id"],
            "well_name": df["transformation_source_well"],
            "volume": df["spotting_volume"]
        })
    
    source_config = {
        "custom_df_func": source_df_func,
        "labware_key": "transformation_plate_name",
        "location_value": "thermocycler"
    }
    
    df_source = process_reactant(df, source_config, params)
    df_all_reactants.append(df_source)
    
    def dest_df_func(df, config, params):
        dest_df = pd.DataFrame({
            "id": df["sample_id"],
            "well_name": df["spotting_well"],
            "volume": df["spotting_volume"],
            "location": df["agar_plate_slot"],
            "labware": params["agar_plate_name"]
        })
        return dest_df
    
    dest_config = {
        "custom_df_func": dest_df_func
    }
    
    df_dest = process_reactant(df, dest_config, params)
    df_all_reactants.append(df_dest)
    
    result_df = pd.concat(df_all_reactants, ignore_index=True)
    result_df = result_df[["id", "location", "labware", "well_name", "volume"]]
    result_df.to_csv(output_csv, index=False)


def create_csv_protocol_3(data_csv: str, parameters_json: str, output_csv: str) -> None:
    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as file:
        params = json.load(file)

    df_all_reactants = []
    
    def source_df_func(df, config, params):
        return pd.DataFrame({
            "id": df["colony_id"],
            "well_name": df["colony_source_well"],
            "volume": 0,
            "location": df["agar_plate_location"]
        })
    
    source_config = {
        "custom_df_func": source_df_func,
        "labware_key": "agar_plate_name"
    }
    
    df_source = process_reactant(df, source_config, params)
    df_all_reactants.append(df_source)
    
    media_grouped = df.groupby(["media_id", "media_source_well"])["media_volume"].sum().reset_index()
    
    def media_df_func(media_grouped, config, params):
        return pd.DataFrame({
            "id": media_grouped["media_id"],
            "well_name": media_grouped["media_source_well"],
            "volume": media_grouped["media_volume"]
        })
    
    media_config = {
        "custom_df_func": media_df_func,
        "location_key": "media_plate_slot",
        "labware_key": "media_plate_name"
    }
    
    df_media = process_reactant(media_grouped, media_config, params)
    df_all_reactants.append(df_media)
    
    def dest_df_func(df, config, params):
        return pd.DataFrame({
            "id": df.apply(lambda row: f'{row["colony_id"]}/{row["media_id"]}', axis=1),
            "well_name": df["destination_well"],
            "volume": df["media_volume"]
        })
    
    dest_config = {
        "custom_df_func": dest_df_func,
        "location_key": "destination_plate_slot",
        "labware_key": "destination_plate_name"
    }
    
    df_dest = process_reactant(df, dest_config, params)
    df_all_reactants.append(df_dest)
    
    result_df = pd.concat(df_all_reactants, ignore_index=True)
    result_df = result_df.reindex(columns=["id", "location", "labware", "well_name", "volume"])
    result_df.to_csv(output_csv, index=False)


def create_csv_protocol_4(data_csv, parameters_json, output_csv):
    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as f:
        plate_slots = json.load(f)

    df_all_reactants = []
    
    reactants = ["culture", "media", "inducer"]
    for reactant in reactants:
        reactant_config = {
            "well_col": f"{reactant}_source_well",
            "volume_col": f"{reactant}_volume",
            "id_col": f"{reactant}_id",
            "location_key": f"{reactant}_plate_slot",
            "labware_key": f"{reactant}_plate_name"
        }
        df_reactant = process_reactant(df, reactant_config, plate_slots)
        df_all_reactants.append(df_reactant)
    
    def destination_df_func(df, config, plate_slots):
        return pd.DataFrame({
            "id": df.apply(lambda row: f'{row["culture_id"]}/{row["media_id"]}/{row["inducer_id"]}', axis=1),
            "well_name": df["destination_well"],
            "volume": df[["culture_volume", "media_volume", "inducer_volume"]].sum(axis=1)
        })
    
    destination_config = {
        "custom_df_func": destination_df_func,
        "location_key": "destination_plate_slot",
        "labware_key": "destination_plate_name"
    }
    
    df_destination = process_reactant(df, destination_config, plate_slots)
    df_all_reactants.append(df_destination)
    
    result_df = pd.concat(df_all_reactants, ignore_index=True)
    result_df = result_df.reindex(columns=["id", "location", "labware", "well_name", "volume"])
    result_df.to_csv(output_csv, index=False)


def create_csv_protocol_5(data_csv, parameters_json, output_csv):
    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as f:
        plate_slots = json.load(f)

    df_all_reactants = []
    
    reagents = {"water": "water", "mastermix": "mastermix"}
    for reactant, reagent_id in reagents.items():
        df_grouped = df.groupby(f"{reactant}_source_well")[f"{reactant}_volume"].sum().reset_index()
        
        def reagent_df_func(df_grouped, config, plate_slots):
            return pd.DataFrame({
                "id": config["fixed_id"],
                "well_name": df_grouped[f"{config['reagent_name']}_source_well"],
                "volume": df_grouped[f"{config['reagent_name']}_volume"]
            })
        
        reactant_config = {
            "custom_df_func": reagent_df_func,
            "fixed_id": reagent_id,
            "reagent_name": reactant,
            "location_key": "reagent_plate_slot",
            "labware_key": "reagent_plate_name"
        }
        df_reactant = process_reactant(df_grouped, reactant_config, plate_slots)
        df_all_reactants.append(df_reactant)
    
    # Process destination plate
    def destination_df_func(df, config, plate_slots):
        return pd.DataFrame({
            "id": df["sample_id"],
            "well_name": df["destination_well"],
            "volume": df[["water_volume", "mastermix_volume"]].sum(axis=1)
        })
    
    destination_config = {
        "custom_df_func": destination_df_func,
        "labware_key": "pcr_plate_name",
        "location_value": "thermocycler"
    }
    
    df_destination = process_reactant(df, destination_config, plate_slots)
    df_all_reactants.append(df_destination)
    
    # Combine all data and save
    result_df = pd.concat(df_all_reactants, ignore_index=True)
    result_df = result_df.reindex(columns=["id", "location", "labware", "well_name", "volume"])
    result_df.to_csv(output_csv, index=False)

def create_csv_protocol_6(data_csv, parameters_json, output_csv):
    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as f:
        plate_slots = json.load(f)

    df_all_reactants = []
    
    culture_config = {
        "well_col": "culture_source_well",
        "volume_col": "culture_volume",
        "id_col": "sample_id",
        "location_key": "culture_plate_slot",
        "labware_key": "culture_plate_name"
    }
    df_culture = process_reactant(df, culture_config, plate_slots)
    df_all_reactants.append(df_culture)
    
    reagent_ids = {"lysis": "lysis buffer", "sds": "SDS buffer"}
    for reactant, reagent_id in reagent_ids.items():
        df_grouped = df.groupby(f"{reactant}_source_well")[f"{reactant}_volume"].sum().reset_index()
        
        def reagent_df_func(df_grouped, config, plate_slots):
            return pd.DataFrame({
                "id": config["fixed_id"],
                "well_name": df_grouped[config["well_col"]],
                "volume": df_grouped[config["volume_col"]]
            })
        
        reactant_config = {
            "custom_df_func": reagent_df_func,
            "fixed_id": reagent_id,
            "well_col": f"{reactant}_source_well",
            "volume_col": f"{reactant}_volume",
            "location_key": "reagent_plate_slot",
            "labware_key": "reagent_plate_name"
        }
        df_reactant = process_reactant(df_grouped, reactant_config, plate_slots)
        df_all_reactants.append(df_reactant)
    
    def lysate_df_func(df, config, plate_slots):
        return pd.DataFrame({
            "id": df["sample_id"],
            "well_name": df["destination_well"],
            "volume": df["lysis_volume"]
        })
    
    lysate_config = {
        "custom_df_func": lysate_df_func,
        "location_key": "lysate_plate_slot",
        "labware_key": "lysate_plate_name"
    }
    
    df_lysate = process_reactant(df, lysate_config, plate_slots)
    df_all_reactants.append(df_lysate)
    
    def destination_df_func(df, config, plate_slots):
        return pd.DataFrame({
            "id": df["sample_id"],
            "well_name": df["destination_well"],
            "volume": df[["sds_volume", "lysis_volume"]].sum(axis=1)
        })
    
    destination_config = {
        "custom_df_func": destination_df_func,
        "labware_key": "destination_plate_name",
        "location_value": "thermocycler"
    }
    
    df_destination = process_reactant(df, destination_config, plate_slots)
    df_all_reactants.append(df_destination)
    
    result_df = pd.concat(df_all_reactants, ignore_index=True)
    result_df = result_df.reindex(columns=["id", "location", "labware", "well_name", "volume"])
    result_df.to_csv(output_csv, index=False)

def create_csv_protocol_7(data_csv, parameters_json, output_csv):
    df = pd.read_csv(data_csv)
    with open(parameters_json, "r") as f:
        plate_slots = json.load(f)

    df_all_reactants = []
    
    reactants = ["diluent", "culture"]
    for reactant in reactants:
        reactant_config = {
            "well_col": f"{reactant}_source_well",
            "volume_col": f"{reactant}_volume",
            "id_col": f"{reactant}_id",
            "location_key": f"{reactant}_plate_slot",
            "labware_key": f"{reactant}_plate_name"
        }
        df_reactant = process_reactant(df, reactant_config, plate_slots)
        df_all_reactants.append(df_reactant)
    
    def destination_df_func(df, config, plate_slots):
        return pd.DataFrame({
            "id": df["culture_id"],
            "well_name": df["destination_well"],
            "volume": df[["diluent_volume", "culture_volume"]].sum(axis=1)
        })
    
    destination_config = {
        "custom_df_func": destination_df_func,
        "location_key": "reading_plate_slot",
        "labware_key": "reading_plate_name"
    }
    
    df_destination = process_reactant(df, destination_config, plate_slots)
    df_all_reactants.append(df_destination)
    
    result_df = pd.concat(df_all_reactants, ignore_index=True)
    result_df = result_df.reindex(columns=["id", "location", "labware", "well_name", "volume"])
    result_df.to_csv(output_csv, index=False)

def main():
    args = docopt(__doc__)
    csv_data = args["<csv_file>"]
    json_data = args["<json_file>"]
    csv_output = args["<output_file>"]

    for i in range(1, 8):
        if str(i) in csv_data:
            protocol_func = globals()[f"create_csv_protocol_{i}"]
            protocol_func(csv_data, json_data, csv_output)
            break

if __name__ == "__main__":
    main()