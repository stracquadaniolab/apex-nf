from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional

metadata = {
    "apiLevel": "2.13",
    "protocolName": "Protocol 4 - Protein Expression Induction",
    "description": "OT-2 protocol for inducing the protein expression.",
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
    
    protocol_data = namedtuple("protocol_data", ["source_id","agar_plate_location","agar_plate_weight","media_source_well","sampling_source_well","media_volume","destination_well"])
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

def choose_pipette_volume(volumes: List[float]) -> str:
    """
    Select appropriate pipette based on the volumes.
    """
    volumes = [volume for volume in volumes if volume != 0]
    min_volume = min(volumes)
    if min_volume <= 20:
        return "p20"
    elif min_volume > 20:
        return "p300"
    else:
        return "Volumes out of range for available pipettes"

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
        
def filter_and_transfer(sources: List[str], destinations: List[str], volumes: List[float]) -> Tuple[List[str], List[str], List[float]]:
    """
    Filter out "NA" values and return filtered sources, destinations, and volumes.
    """
    filtered_indices = [i for i, source in enumerate(sources) if source != "NA"]
    return ([sources[i] for i in filtered_indices], 
            [destinations[i] for i in filtered_indices], 
            [volumes[i] for i in filtered_indices])

def run(protocol: protocol_api.ProtocolContext):
    """
    Main function for running the protocol.
    """
    json_params = load_experiment_parameters(json_parameters) # load the parameters from the json file
    single, multi = load_experiment_data(csv_data) # load data from the csv file, modified based on the channel of the pipette

    # Load pipettes
    right_pipette_tipracks = [protocol.load_labware(load_name=json_params["right_pipette_tiprack_name"], location=i) for i in json_params["right_pipette_tiprack_slot"]]
    right_pipette = protocol.load_instrument(instrument_name=json_params["right_pipette_name"], mount=json_params["right_pipette_mount"], tip_racks=right_pipette_tipracks)
    left_pipette_tipracks = [protocol.load_labware(load_name=json_params["left_pipette_tiprack_name"], location=i) for i in json_params["left_pipette_tiprack_slot"]]
    left_pipette = protocol.load_instrument(instrument_name=json_params["left_pipette_name"], mount=json_params["left_pipette_mount"], tip_racks=left_pipette_tipracks)
    
    pipette_culture = right_pipette if choose_pipette_volume(single.culture_volume) in json_params["right_pipette_name"] else left_pipette # Choose which pipette to use based on volume
    pipette_inducer = right_pipette if choose_pipette_volume(single.inducer_volume) in json_params["right_pipette_name"] else left_pipette
    pipette_blank = right_pipette if choose_pipette_volume(single.blank_volume) in json_params["right_pipette_name"] else left_pipette

    pipette_channel_culture = multi if choose_pipette_channel(str(pipette_culture)) == "multi" else single # Choose the csv wells based on the pipette being used
    pipette_channel_inducer = multi if choose_pipette_channel(str(pipette_inducer)) == "multi" else single
    pipette_channel_blank = multi if choose_pipette_channel(str(pipette_blank)) == "multi" else single

    # Load hardware and labware
    loaded_plates = {} # Dictionary to keep track of loaded plates
    blank_plate = load_or_reuse_labware(protocol, {"name": json_params["blank_plate_name"], "slot": json_params["blank_plate_slot"]}, loaded_plates)
    culture_plate = load_or_reuse_labware(protocol, {"name": json_params["culture_plate_name"], "slot": json_params["culture_plate_slot"]}, loaded_plates)
    inducer_plate = load_or_reuse_labware(protocol, {"name": json_params["inducer_plate_name"], "slot": json_params["inducer_plate_slot"]}, loaded_plates)
    destination_plate = load_or_reuse_labware(protocol, {"name": json_params["destination_plate_name"], "slot": json_params["destination_plate_slot"]}, loaded_plates)

    ########## BLANK TRANSFER ##########
    source, destination, volume = filter_and_transfer(pipette_channel_blank.blank_well, pipette_channel_blank.destination_well, pipette_channel_blank.blank_volume)
    pipette_culture.transfer(volume=volume,
                            source=[blank_plate.wells_by_name()[well] for well in source],
                            dest=[destination_plate.wells_by_name()[well] for well in destination],
                            new_tip="once")

    ##### TRANSFERRING CULTURE TO A PLATE SUITABLE FOR THE READER ##########
    source, destination, volume = filter_and_transfer(pipette_channel_culture.culture_well, pipette_channel_culture.destination_well, pipette_channel_culture.culture_volume)
    pipette_culture.distribute(volume=volume,
                            source=[culture_plate.wells_by_name()[well] for well in source],
                            dest=[destination_plate.wells_by_name()[well] for well in destination],
                            mix_before=(2,pipette_culture.max_volume/2),
                            new_tip="once")
    protocol.pause("Take t0 measurement")
    
    ######## TRANSFERRING THE INDUCER ##########
    source, destination, volume = filter_and_transfer(pipette_channel_inducer.inducer_well, pipette_channel_inducer.destination_well, pipette_channel_inducer.inducer_volume)
    pipette_inducer.transfer(volume=volume,
                            source=[inducer_plate.wells_by_name()[well] for well in source],
                            dest=[destination_plate.wells_by_name()[well] for well in destination],
                            mix_before=(1,pipette_inducer.max_volume/2),
                            mix_after=(3,pipette_inducer.max_volume/2),
                            new_tip="always")