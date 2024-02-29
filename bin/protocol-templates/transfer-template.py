from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional

metadata = {
    "apiLevel": "2.13",
    "protocolName": "Simple liquid transfer protocol",
    "description": "OT-2 protocol for transferring liquids.",
    "author": "Martyna Kasprzyk"
}

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
    csv_data = csv.DictReader(csv_file.splitlines())

    single_channel_wells, multi_channel_wells = [],[] # List of wells when single or multi channel pipette is used
    columns = defaultdict(list)

    for row in csv_data:
        single_channel_wells.append(row) # For single channel the list of wells stays as provided in the csv file
        well = row["destination_well"]
        _, column_number = well[0], well[1:] # For multi
        if column_number not in columns:
            multi_channel_wells.append(row)
            columns[column_number].append(well)
    
    protocol_data = namedtuple("protocol_data", ["source_ID", "destination_ID", "source_well", "destination_well", "volume"])
    single_channel_data = extract_data(single_channel_wells)
    multi_channel_data = extract_data(multi_channel_wells)
    return protocol_data(*single_channel_data), protocol_data(*multi_channel_data)

def extract_data(rows: List[Dict]) -> Tuple[List[str], ...]:
    """
    Extarct the required info for the protocol.
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

def load_or_reuse_labware(protocol: protocol_api.ProtocolContext, plate_info: Dict[str, str], loaded_plates: Dict[str, protocol_api.Labware]):
    """
    Load a plate into the protocol or reuse an existing one if the slot is already occupied.
    """    
    slot = plate_info["slot"]
    if slot in loaded_plates:
        return loaded_plates[slot] # Reuse the plate that"s already loaded into this slot
    else:
        plate = protocol.load_labware(plate_info["name"], slot) 
        loaded_plates[slot] = plate # Load a new plate and store it in the dictionary
        return plate

def run(protocol: protocol_api.ProtocolContext):
    """
    Main function for running the protocol.
    """
    json_params = load_experiment_parameters(json_parameters) # load the parameters from the json file
    single, multi = load_experiment_data(csv_data) # load data from the csv file, modified based on the channel of the pipette

    # Load pipettes
    pipette_tipracks = [protocol.load_labware(load_name=json_params["pipette_tiprack_name"], location=i) for i in json_params["pipette_tiprack_slots"]]
    pipette = protocol.load_instrument(instrument_name=json_params["pipette_name"], mount=json_params["pipette_mount"], tip_racks=pipette_tipracks)
    pipette_channel = multi if choose_pipette_channel(str(pipette)) == "multi" else single # Choose the csv wells based on the pipette being used
    
    # Load hardware and labware
    loaded_plates = {} # Dictionary to keep track of loaded plates
    source_plate = load_or_reuse_labware(protocol, {"name": json_params["source_plate_name"], "slot": json_params["source_plate_slot"]}, loaded_plates)
    destination_plate = load_or_reuse_labware(protocol, {"name": json_params["destination_plate_name"], "slot": json_params["destination_plate_slot"]}, loaded_plates)

    ######## LIQUID TRANSFER ##########
    pipette.transfer(volume=pipette_channel.volume,
                    source=[source_plate.wells_by_name()[well] for well in pipette_channel.source_well],
                    dest=[destination_plate.wells_by_name()[well] for well in pipette_channel.destination_well],
                    new_tip = json_params["ew_tip_use"],
                    mix_before=(3,pipette.max_volume),
                    mix_after=(3,pipette.max_volume))