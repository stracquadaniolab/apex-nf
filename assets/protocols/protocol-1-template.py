from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional

metadata = {
    "apiLevel": "2.13",
    "protocolName": "Protocol 1: E. coli heat-shock transformation",
    "description": "OT-2 protocol for standard E. coli heat-shock transformation using thermocycler.",
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
    
    protocol_data = namedtuple("protocol_data", ["dna_id", "dna_well", "dna_volume", "cells_id", "cells_well", "cells_volume", "media_id", "media_well", "media_volume", "destination_well"])
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
        return None

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
        return loaded_plates[slot] # Reuse the plate that's already loaded into this slot
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
    json_params = load_experiment_parameters(INPUT_JSON_FILE) # Load the parameters from the json file
    single, multi = load_experiment_data(INPUT_CSV_FILE) # Load data from the csv file, modified based on the channel of the pipette

    # Load pipettes
    right_pipette_tipracks = [protocol.load_labware(load_name=json_params["right_pipette_tiprack_name"], location=i) for i in json_params["right_pipette_tiprack_slot"]]
    right_pipette = protocol.load_instrument(instrument_name=json_params["right_pipette_name"], mount="right", tip_racks=right_pipette_tipracks)
    left_pipette_tipracks = [protocol.load_labware(load_name=json_params["left_pipette_tiprack_name"], location=i) for i in json_params["left_pipette_tiprack_slot"]]
    left_pipette = protocol.load_instrument(instrument_name=json_params["left_pipette_name"], mount="left", tip_racks=left_pipette_tipracks)
    pipette_cells = right_pipette if choose_pipette_volume(single.cells_volume) in json_params["right_pipette_name"] else left_pipette # Choose which pipette to use based on volume
    pipette_dna = right_pipette if choose_pipette_volume(single.dna_volume) in json_params["right_pipette_name"] else left_pipette
    pipette_media = right_pipette if choose_pipette_volume(single.media_volume) in json_params["right_pipette_name"] else left_pipette
    pipette_channel_cells = multi if choose_pipette_channel(str(pipette_cells)) == "multi" else single # Choose the csv wells based on the pipette being used
    pipette_channel_dna = multi if choose_pipette_channel(str(pipette_dna)) == "multi" else single
    pipette_channel_media = multi if choose_pipette_channel(str(pipette_media)) == 'multi' else single
    
    # Load hardware and labware
    loaded_plates = {} # Dictionary to keep track of loaded plates
    cells_plate = load_or_reuse_labware(protocol, {"name": json_params["cells_plate_name"], "slot": json_params["cells_plate_slot"]}, loaded_plates)
    dna_plate = load_or_reuse_labware(protocol, {"name": json_params["dna_plate_name"], "slot": json_params["dna_plate_slot"]}, loaded_plates)
    media_plate = load_or_reuse_labware(protocol, {"name": json_params["media_plate_name"], "slot": json_params["media_plate_slot"]}, loaded_plates)
    cells_plate = load_or_reuse_labware(protocol, {"name": json_params["cells_plate_name"], "slot": json_params["cells_plate_slot"]}, loaded_plates)
    
    protocol.set_rail_lights(True)

    if json_params["destination_plate_slot"] ==  "thermocycler":
        thermocycler_mod = protocol.load_module("thermocycler")  # Load the thermocycler module which takes location 7,8,10,11
        destination_plate = thermocycler_mod.load_labware(json_params["destination_plate_name"])
        thermocycler_mod.set_block_temperature(temperature=json_params["pre_shock_incubation_temp"])
        thermocycler_mod.open_lid()
        protocol.pause("Put plate into the thermocycler module and click 'resume'.")
    else:
        destination_plate = protocol.load_labware(json_params["destination_plate_name"], json_params["destination_plate_slot"])

    ########## ADD COMPETENT CELLS ##########
    cells_source, cells_destination, cells_volume = filter_and_transfer(pipette_channel_cells.cells_well, pipette_channel_cells.destination_well, pipette_channel_cells.cells_volume)
    pipette_cells.pick_up_tip()
    # Set to keep track of wells that have been mixed
    mixed_wells = set()
    for well, volume in zip(cells_source, cells_volume):
        if well not in mixed_wells:
            # Mix the well if it hasn't been mixed yet
            pipette_cells.mix(1, pipette_cells.max_volume, cells_plate.wells_by_name()[well])
            mixed_wells.add(well)
        pipette_cells.transfer(volume=volume,
                            source=cells_plate.wells_by_name()[well],
                            dest=destination_plate.wells_by_name()[well],
                            new_tip="never")
    pipette_cells.drop_tip()
 
    ########## ADD DNA ##########
    pipette_dna.well_bottom_clearance.aspirate = 0.5
    dna_source, dna_destination, dna_volume = filter_and_transfer(pipette_channel_dna.dna_well, pipette_channel_dna.destination_well, pipette_channel_dna.dna_volume)
    for i in zip(dna_source, dna_destination, dna_volume, cells_volume):
        pipette_dna.pick_up_tip()
        pipette_dna.aspirate(volume=i[2], location=dna_plate.wells_by_name()[i[0]])
        pipette_dna.dispense(volume=i[2], location=destination_plate.wells_by_name()[i[1]])
        mixing_volume = (i[2]+i[3])/2
        pipette_dna.mix(repetitions=2, volume=mixing_volume, location=destination_plate.wells_by_name()[i[1]])
        pipette_dna.blow_out(location=destination_plate.wells_by_name()[i[1]])
        pipette_dna.move_to(destination_plate.wells_by_name()[i[1]].bottom()) # To make sure that the droplets from the blow out do not stay on the tip
        pipette_dna.drop_tip()

    ########## HEAT-SHOCK TRANSFORMATION ##########
    if json_params["destination_plate_slot"] ==  "thermocycler":
        thermocycler_mod.close_lid()
        thermocycler_mod.set_block_temperature(temperature=json_params["pre_shock_incubation_temp"], 
                                            hold_time_minutes=json_params["pre_shock_incubation_time"])
        protocol.comment("Starting heat-shock transformation.")
        thermocycler_mod.set_block_temperature(temperature=json_params["heat_shock_temp"], 
                                            hold_time_seconds=json_params["heat_shock_time"])
        thermocycler_mod.set_block_temperature(temperature=json_params["post_shock_incubation_temp"],
                                            hold_time_minutes=json_params["post_shock_incubation_time"])
        thermocycler_mod.open_lid()
    else:
        protocol.pause("Put plate into an external thermocycler for heat-shock transformation and return.")

    ######## ADD RECOVERY MEDIUM ##########
    media_source, media_destination, media_volume = filter_and_transfer(pipette_channel_media.media_well, pipette_channel_media.destination_well, pipette_channel_media.media_volume)
    for i in zip(media_source, media_destination, media_volume, cells_volume):
        pipette_media.pick_up_tip()
        pipette_media.aspirate(volume=i[2], location=media_plate.wells_by_name()[i[0]])
        pipette_media.dispense(volume=i[2], location=destination_plate.wells_by_name()[i[1]])
        mixing_volume = (i[2]+i[3])/2
        for _ in range(3):
            pipette_media.aspirate(volume=mixing_volume, location=destination_plate.wells_by_name()[i[1]])
            pipette_media.dispense(volume=mixing_volume, location=destination_plate.wells_by_name()[i[1]])
        pipette_media.blow_out(location=destination_plate.wells_by_name()[i[1]])
        pipette_media.move_to(destination_plate.wells_by_name()[i[1]].bottom())
        pipette_media.drop_tip()
    
    ######## RECOVERY INCUBATION ##########
    if json_params["destination_plate_slot"] ==  "thermocycler":

        thermocycler_mod.close_lid()
        thermocycler_mod.set_lid_temperature(temperature=json_params["inc_temp"])
        thermocycler_mod.set_block_temperature(temperature=json_params["inc_temp"], 
                                            hold_time_minutes=json_params["inc_time"])
        thermocycler_mod.deactivate_lid()
        thermocycler_mod.deactivate()
        protocol.set_rail_lights(False)
    else:
        protocol.comment("Put plate into an external thermocycler for incubation.")