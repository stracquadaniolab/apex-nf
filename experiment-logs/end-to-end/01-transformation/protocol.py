csv_data = """dna_ID,dna_well,dna_volume,cells_ID,cells_well,cells_volume,media_ID,media_well,media_volume,transformation_well
water,A1,3,BL21(DE3),A2,30,SOC,A3,150,A1
pUC19,B1,3,BL21(DE3),B2,30,SOC,B3,150,B1
pJKR,C1,3,BL21(DE3),C2,30,SOC,C3,150,C1
pJKR,D1,3,BL21(DE3),D2,30,SOC,D3,150,D1
pJKR,E1,3,BL21(DE3),E2,30,SOC,E3,150,E1
pJKR,F1,3,BL21(DE3),F2,30,SOC,F3,150,F1
pJKR,G1,3,BL21(DE3),G2,30,SOC,G3,150,G1
pJKR,H1,3,BL21(DE3),H2,30,SOC,H3,150,H1"""

json_parameters = """{
    "right_pipette_tiprack_name":"opentrons_96_tiprack_20ul",
    "right_pipette_tiprack_slot":[2,3],
    "right_pipette_name":"p20_multi_gen2",
    "right_pipette_mount":"right",
    "left_pipette_tiprack_name":"opentrons_96_tiprack_300ul",
    "left_pipette_tiprack_slot":[6,9],
    "left_pipette_name":"p300_multi_gen2",
    "left_pipette_mount":"left",
    "dna_plate_name":"armadillo_96_wellplate_200ul_pcr_full_skirt",
    "dna_plate_slot":1,
    "cells_plate_name": "armadillo_96_wellplate_200ul_pcr_full_skirt",
    "cells_plate_slot":1,
    "media_plate_name": "armadillo_96_wellplate_200ul_pcr_full_skirt",
    "media_plate_slot": 1,
    "transformation_plate_name":"armadillo_96_wellplate_200ul_pcr_full_skirt",
    "init_temp":4,
    "init_time":20,
    "heat_temp":42,
    "heat_time":30,
    "cool_temp":4,
    "cool_time":2,
    "inc_temp":37,
    "inc_time":60
}"""

from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional

metadata = {
    "apiLevel": "2.13",
    "protocolName": "E. coli heat-shock transformation",
    "description": "OT-2 protocol for standard E. coli heat-shock transformation using thermocycler.",
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
    
    protocol_data = namedtuple("protocol_data", ["cells_well", "cells_volume", "dna_well", "dna_volume", "media_well", "media_volume", "transformation_well"])
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
    pipette_cells = right_pipette if choose_pipette_volume(single.cells_volume) in json_params["right_pipette_name"] else left_pipette # Choose which pipette to use based on volume
    pipette_dna = right_pipette if choose_pipette_volume(single.dna_volume) in json_params["right_pipette_name"] else left_pipette
    pipette_media = right_pipette if choose_pipette_volume(single.media_volume) in json_params["right_pipette_name"] else left_pipette
    pipette_channel_cells = multi if choose_pipette_channel(str(pipette_cells)) == "multi" else single # Choose the csv wells based on the pipette being used
    pipette_channel_dna = multi if choose_pipette_channel(str(pipette_dna)) == "multi" else single
    pipette_channel_soc = multi if choose_pipette_channel(str(pipette_media)) == multi else single
    
    # Load hardware and labware
    loaded_plates = {} # Dictionary to keep track of loaded plates
    cells_plate = load_or_reuse_labware(protocol, {"name": json_params["cells_plate_name"], "slot": json_params["cells_plate_slot"]}, loaded_plates)
    dna_plate = load_or_reuse_labware(protocol, {"name": json_params["dna_plate_name"], "slot": json_params["dna_plate_slot"]}, loaded_plates)
    soc_plate = load_or_reuse_labware(protocol, {"name": json_params["media_plate_name"], "slot": json_params["media_plate_slot"]}, loaded_plates)
    cells_plate = load_or_reuse_labware(protocol, {"name": json_params["cells_plate_name"], "slot": json_params["cells_plate_slot"]}, loaded_plates)
    thermocycler_mod = protocol.load_module("thermocycler")  # Load the thermocycler module which takes location 7,8,10,11
    transformation_plate = thermocycler_mod.load_labware(json_params["transformation_plate_name"]) # Plate where transformations take place, loaded onto thermocycler module

    ########## COMPETENT CELLS TRANSFER ##########
    pipette_cells.transfer(volume=pipette_channel_cells.cells_volume,
                    source=[cells_plate.wells_by_name()[well] for well in pipette_channel_cells.cells_well], # transfer from the specified well in the resevoir containing competent cells
                    dest=[transformation_plate.wells_by_name()[well] for well in pipette_channel_cells.transformation_well], # transfer to transformation plate in the thermocycler
                    new_tip = "once",
                    mix_before=(1,pipette_cells.max_volume)) # Resuspend the competent cells once before transferring into the transformation plate 

    ########## DNA TRANSFER ##########
    for i in zip(pipette_channel_dna.dna_well, pipette_channel_dna.transformation_well, pipette_channel_dna.dna_volume, pipette_channel_dna.cells_volume):
        pipette_dna.pick_up_tip()
        pipette_dna.aspirate(volume=i[2], location=dna_plate.wells_by_name()[i[0]])
        pipette_dna.dispense(volume=i[2], location=transformation_plate.wells_by_name()[i[1]])
        mixing_volume = (i[2]+i[3])/2
        pipette_dna.mix(repetitions=2, volume=mixing_volume, location=transformation_plate.wells_by_name()[i[1]], rate=2)
        pipette_dna.blow_out(location=transformation_plate.wells_by_name()[i[1]])
        pipette_dna.move_to(transformation_plate.wells_by_name()[i[1]].bottom()) # To make sure that the droplets from the blow out do not stay on the tip
        pipette_dna.drop_tip()

    ########## RECOVERY MEDIUM TRANSFER ##########
    for i in zip(pipette_channel_soc.media_well, pipette_channel_soc.transformation_well, pipette_channel_soc.media_volume, pipette_channel_soc.dna_volume, pipette_channel_soc.cells_volume):
        pipette_media.pick_up_tip()
        pipette_media.aspirate(volume=i[2], location=soc_plate.wells_by_name()[i[0]])
        pipette_media.dispense(volume=i[2], location=transformation_plate.wells_by_name()[i[1]])
        mixing_volume = (i[2]+i[3]+i[4])/2
        for _ in range(3):
            pipette_media.aspirate(volume=mixing_volume, location=transformation_plate.wells_by_name()[i[1]])
            pipette_media.dispense(volume=mixing_volume, location=transformation_plate.wells_by_name()[i[1]])
        pipette_media.blow_out(location=transformation_plate.wells_by_name()[i[1]])
        pipette_media.move_to(transformation_plate.wells_by_name()[i[1]].bottom())
        pipette_media.drop_tip()