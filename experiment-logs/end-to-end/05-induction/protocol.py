csv_data = """ID,blank_well,blank_volume,culture_well,culture_volume,inducer_well,inducer_volume,destination_well
LB+carbenicillin,A7,150,NA,0,NA,0,A1
LB+carbenicillin,B7,150,NA,0,NA,0,B1
LB+carbenicillin,C7,150,NA,0,NA,0,C1
BL21(DE3),NA,0,A6,150,NA,0,A2
BL21(DE3),NA,0,B6,150,NA,0,B2
BL21(DE3),NA,0,C6,150,NA,0,C2
BL21(DE3),NA,0,D6,150,NA,0,D2
BL21(DE3),NA,0,E6,150,NA,0,E2
BL21(DE3),NA,0,F6,150,NA,0,F2
BL21(DE3),NA,0,G6,150,NA,0,G2
BL21(DE3),NA,0,H6,150,NA,0,H2
BL21(DE3),NA,0,A6,150,NA,0,A3
BL21(DE3),NA,0,B6,150,NA,0,B3
BL21(DE3),NA,0,C6,150,NA,0,C3
BL21(DE3),NA,0,D6,150,NA,0,D3
BL21(DE3),NA,0,E6,150,NA,0,E3
BL21(DE3),NA,0,F6,150,NA,0,F3
BL21(DE3),NA,0,G6,150,NA,0,G3
BL21(DE3),NA,0,H6,150,NA,0,H3
BL21(DE3),NA,0,A6,150,NA,0,A4
BL21(DE3),NA,0,B6,150,NA,0,B4
BL21(DE3),NA,0,C6,150,NA,0,C4
BL21(DE3),NA,0,D6,150,NA,0,D4
BL21(DE3),NA,0,E6,150,NA,0,E4
BL21(DE3),NA,0,F6,150,NA,0,F4
BL21(DE3),NA,0,G6,150,NA,0,G4
BL21(DE3),NA,0,H6,150,NA,0,H4
arabinose,NA,0,A6,150,A8,3.68,A5
arabinose,NA,0,B6,150,B8,3.68,B5
arabinose,NA,0,C6,150,C8,3.68,C5
arabinose,NA,0,D6,150,D8,3.68,D5
arabinose,NA,0,E6,150,E8,3.68,E5
arabinose,NA,0,F6,150,F8,3.68,F5
arabinose,NA,0,G6,150,G8,3.68,G5
arabinose,NA,0,H6,150,H8,3.68,H5
arabinose,NA,0,A6,150,A8,3.68,A6
arabinose,NA,0,B6,150,B8,3.68,B6
arabinose,NA,0,C6,150,C8,3.68,C6
arabinose,NA,0,D6,150,D8,3.68,D6
arabinose,NA,0,E6,150,E8,3.68,E6
arabinose,NA,0,F6,150,F8,3.68,F6
arabinose,NA,0,G6,150,G8,3.68,G6
arabinose,NA,0,H6,150,H8,3.68,H6
arabinose,NA,0,A6,150,A8,3.68,A7
arabinose,NA,0,B6,150,B8,3.68,B7
arabinose,NA,0,C6,150,C8,3.68,C7
arabinose,NA,0,D6,150,D8,3.68,D7
arabinose,NA,0,E6,150,E8,3.68,E7
arabinose,NA,0,F6,150,F8,3.68,F7
arabinose,NA,0,G6,150,G8,3.68,G7
arabinose,NA,0,H6,150,H8,3.68,H7"""

json_parameters = """{
    "right_pipette_tiprack_name":"opentrons_96_tiprack_20ul",
    "right_pipette_tiprack_slot":[6],
    "right_pipette_name":"p20_multi_gen2",
    "right_pipette_mount":"right",
    "left_pipette_tiprack_name":"opentrons_96_tiprack_300ul",
    "left_pipette_tiprack_slot":[9],
    "left_pipette_name":"p300_multi_gen2",
    "left_pipette_mount":"left",
    "blank_plate_name":"usascientific_96_wellplate_2.4ml_deep",
    "blank_plate_slot":3,
    "culture_plate_name":"usascientific_96_wellplate_2.4ml_deep",
    "culture_plate_slot":3,
    "inducer_plate_name":"usascientific_96_wellplate_2.4ml_deep",
    "inducer_plate_slot":3,
    "destination_plate_name":"armadillo_96_wellplate_200ul_pcr_full_skirt",
    "destination_plate_slot":2
}"""

from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional

metadata = {
    "apiLevel": "2.13",
    "protocolName": "Protein expression induction",
    "description": "OT-2 protocol for inducing the protein expression.",
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
    
    protocol_data = namedtuple("protocol_data", ["ID", "blank_well", "blank_volume", "culture_well", "culture_volume", "inducer_well", "inducer_volume", "destination_well"])
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
