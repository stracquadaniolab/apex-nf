from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional
import math

metadata = {
    "apiLevel": "2.13",
    "protocolName": "Protocol 2 - Agar Plate Spotting",
    "description": "OT-2 protocol for agar plate spotting.",
    "author": "Martyna Kasprzyk"
}

##############################################
##### PROTOCOL-COMPILER: DO NOT CHANGE   #####
##############################################

# PROTOCOL CONFIGURATION FILE
INPUT_JSON_FILE = """
{{INPUT_JSON_FILE}}
"""

# PROTOCOL INPUT MATERIAL
INPUT_CSV_FILE = """
{{INPUT_CSV_FILE}}
"""

##############################################


def load_experiment_parameters(json_file: str) -> dict:
    """
    Load and return experiment parameters from a JSON file.
    """
    experiment_parameters = json.loads(json_file)
    return experiment_parameters

def load_experiment_data(csv_file: str):
    """
    Parse CSV file and return data for single and multi-channel pipettes.
    """
    csv_data = csv.DictReader(csv_file.splitlines()[1:])

    single_channel_wells, multi_channel_wells = [],[] # List of wells when single or multi channel pipette is used
    columns = defaultdict(list)
    for row in csv_data:
        single_channel_wells.append(row) # For single channel the list of wells stays as provided in the csv file
        well = row["destination_well"]
        _, column_number = well[0], well[1:] # For multi
        if column_number not in columns:
            multi_channel_wells.append(row)
            columns[column_number].append(well)
    
    protocol_data = namedtuple("protocol_data", ["id", "agar_plate_location", "source_well", "destination_well", "spotting_volume", "agar_plate_weight"])
    single_channel_data = extract_data(single_channel_wells)
    multi_channel_data = extract_data(multi_channel_wells)
    return protocol_data(*single_channel_data), protocol_data(*multi_channel_data)

def extract_data(rows: List[Dict]) -> Tuple[List[str], ...]:
    """
    Extract the required info for the protocol.
    """
    data = defaultdict(list)
    for row in rows:
        for key in row:
            if key.endswith("volume"):
                data[key].append(float(row[key]))
            else:
                data[key].append(row[key])
    return tuple(data.values())

def choose_pipette_channel(pipette: str) -> str:
    """
    Determine pipette channel based on pipette type.
    """
    if "8-Channel" in pipette:
        return "multi"
    elif "Single-Channel" in pipette:
        return "single"
    else:
        return "Invalid pipette type."

def agar_height(agar_plate_weight: float, empty_agar_plate_weight: float , agar_plate_area: float, agar_density: float, spotting_height: float) -> float:
    """
    Calculate the the agar height based on the base area of the plate, weight of the empty plate, the weight of plate with agar and the agar density.
    """
    agar_weight = float(agar_plate_weight) - float(empty_agar_plate_weight)
    agar_height = agar_weight/(agar_plate_area*agar_density) # Agar height calculation
    height = agar_height + spotting_height # Adds spotting_height i.e. how many mm below or above the agar the robot should dispense
    return height

def run(protocol: protocol_api.ProtocolContext):
    """
    Main function for running the protocol.
    """
    json_params = load_experiment_parameters(INPUT_JSON_FILE) # load the parameters from the json file
    single, multi = load_experiment_data(INPUT_CSV_FILE) # load data from the csv file, modified based on the channel of the pipette

    # Load pipettes
    pipette_tipracks = [protocol.load_labware(load_name=json_params["tiprack_name"], location=i) for i in json_params["tiprack_slots"]]
    pipette = protocol.load_instrument(instrument_name=json_params["pipette_name"], mount=json_params["pipette_mount"], tip_racks=pipette_tipracks)
    pipette_channel = multi if choose_pipette_channel(str(pipette)) == "multi" else single # Choose the csv wells based on the pipette being used

    # Load hardware and labware
    agar_labware = [protocol.load_labware(load_name=json_params["agar_plate_name"],
                                        location=slot,
                                        label=f"Agar Plate {i+1}")
                    for i, slot in enumerate(json_params["agar_plate_slots"])]

    mapping_dict = {int(slot): labware for slot, labware in zip(json_params["agar_plate_slots"], agar_labware)} # Create a mapping dictionary from slot to agar_labware
    agar_plates = [mapping_dict[int(loc)] for loc in pipette_channel.agar_plate_location if int(loc) in mapping_dict] # Generate agar_plates list with repeating plates

    if json_params["source_plate_slot"] == "thermocycler":
        thermocycler_mod = protocol.load_module("thermocycler") # Thermocycler module, takes location 7,8,10,11
        source_plate = thermocycler_mod.load_labware(json_params["source_plate_name"])
        thermocycler_mod.open_lid()
    else:
        source_plate = protocol.load_labware(load_name=json_params["source_plate_name"], location=json_params["source_plate_slot"])
    ######## SPOTTING ##########
    for plate, source, destination, weight, volume in zip(agar_plates, pipette_channel.source_well, pipette_channel.destination_well, pipette_channel.agar_plate_weight, pipette_channel.spotting_volume):
        pipette.well_bottom_clearance.dispense = 1 # Reset the dispense height 
        pipette.pick_up_tip()
        pipette.mix(repetitions=3, volume=pipette.max_volume, location=source_plate[source], rate=2) # Resuspend the transformed cells
        pipette.aspirate(volume=volume + json_params["additional_volume"], location=source_plate[source], rate=2) # Aspirate the spotting volume and dead volume for better accuracy
        pipette.well_bottom_clearance.dispense = agar_height(weight, json_params["empty_agar_plate_weight"], json_params["agar_plate_area"], json_params["agar_density"], json_params["spotting_height"]) #Adjust height to the agar wight
        pipette.dispense(volume=volume, location=plate[destination], rate=4) # Spotting
        protocol.delay(seconds=5)
        pipette.drop_tip()