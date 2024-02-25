from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict

metadata = {
    "apiLevel": "2.13",
    "protocolName": "E. coli heat-shock transformation",
    "description": "OT-2 protocol for standard E. coli heat-shock transformation using thermocycler.",
    "author": "Martyna Kasprzyk",
}

def load_experiment_parameters(json_file: str) -> dict:
    """
    This function parses the json file with the parameters for the experiment and returns them as a dictionary.
    """
    experiment_parameters = json.loads(json_file)
    return experiment_parameters

def load_experiment_data(csv_file: str):
    """
    This function parses the csv file with the data for the experiment and returns them as namedtuples.
    """
    csv_data = csv.DictReader(csv_file.splitlines())

    single_channel_wells = [] # List of wells when single channel pipette is used
    multi_channel_wells = [] # List of wells when multi channel pipette is used
    columns = defaultdict(str)

    for row in csv_data:
        single_channel_wells.append(row) # For single channel the list of wells stays as provided in the csv file
        well = row['dna_well']
        row_letter, column_number = well[0], well[1:] # Well annotation is in the form "A1"
        if not columns[column_number]:
            multi_channel_wells.append(row) # For multi channel the list is modified so only the first well of a column is kept
            columns[column_number] = row_letter
    
    protocol_data = namedtuple("protocol_data", ["cells_well", "cells_volume", "dna_well", "dna_volume", "media_well", "media_volume", "transformation_well"])
    single_channel_data = extract_data(single_channel_wells)
    multi_channel_data = extract_data(multi_channel_wells)
    return protocol_data(*single_channel_data), protocol_data(*multi_channel_data)

def extract_data(rows: list):
    """
    This function extracts the required info for the protocol.
    """
    cells_well = []
    cells_volume = []
    dna_well = []
    dna_volume = []
    media_well = []
    media_volume = []
    transformation_well = []

    for row in rows:
        cells_well.append(row['cells_well'])
        cells_volume.append(int(row["cells_volume"]))
        dna_well.append(row['dna_well'])
        dna_volume.append(int(row["dna_volume"]))
        media_well.append(row['media_well'])
        media_volume.append(int(row["media_volume"]))
        transformation_well.append(row["transformation_well"])

    return cells_well, cells_volume, dna_well, dna_volume, media_well, media_volume, transformation_well

def choose_pipette_volume(volumes: list) -> str:
    """
    This function adjusts which pipette to use for handling DNA, cells and media.
    """
    min_volume = min(volumes)
    if min_volume <= 20:
        return "p20"
    elif min_volume > 20:
        return "p300"
    else:
        return "Volumes out of range for available pipettes"

def choose_pipette_channnel(pipette: str) -> str:
    """
    This function checks which channel is used so it can adjust the wells list.
    """
    if "8-Channel" in pipette:
        return "multi"
    elif "Single-Channel" in pipette:
        return "single"
    else:
        return "Invalid pipette type."
    
def run(protocol: protocol_api.ProtocolContext):
    """
    Main function for running the protocol.
    """
    json_params = load_experiment_parameters(json_parameters) # load the parameters from the json file
    single, multi = load_experiment_data(csv_data) # load data from the csv file, modified based on the channel of the pipette

    # Load hardware and labware
    cells_plate = protocol.load_labware(json_params['cells_plate_name'], json_params['cells_plate_slot'])
    dna_plate = protocol.load_labware(json_params['dna_plate_name'], json_params['dna_plate_slot'])
    soc_plate = protocol.load_labware(json_params['media_plate_name'], json_params['media_plate_slot'])
    right_pipette_tipracks = [protocol.load_labware(load_name=json_params['right_pipette_tiprack_name'], location=i) for i in json_params['right_pipette_tiprack_slot']]
    right_pipette = protocol.load_instrument(instrument_name=json_params["right_pipette_name"], mount=json_params["right_pipette_mount"], tip_racks=right_pipette_tipracks)
    left_pipette_tipracks = [protocol.load_labware(load_name=json_params['left_pipette_tiprack_name'], location=i) for i in json_params['left_pipette_tiprack_slot']]
    left_pipette = protocol.load_instrument(instrument_name=json_params["left_pipette_name"], mount=json_params["left_pipette_mount"], tip_racks=left_pipette_tipracks)
    thermocycler_mod = protocol.load_module("thermocycler")  # Load the thermocycler module which takes location 7,8,10,11
    transformation_plate = thermocycler_mod.load_labware(json_params["transformation_plate_name"]) # Plate where transformations take place, loaded onto thermocycler module

    # Load pipettes
    pipette_cells = right_pipette if choose_pipette_volume(single.cells_volume) in json_params["right_pipette_name"] else left_pipette # Choose which pipette to use based on volume
    pipette_dna = right_pipette if choose_pipette_volume(single.dna_volume) in json_params["right_pipette_name"] else left_pipette
    pipette_media = right_pipette if choose_pipette_volume(single.media_volume) in json_params["right_pipette_name"] else left_pipette
    pipette_channel_cells = multi if choose_pipette_channnel(str(pipette_cells)) == "multi" else single # Choose the csv wells based on the pipette being used
    pipette_channel_dna = multi if choose_pipette_channnel(str(pipette_dna)) == "multi" else single
    pipette_channel_soc = multi if choose_pipette_channnel(str(pipette_media)) == multi else single

    ### COMPETENT CELLS TRANSFER ###
    pipette_cells.transfer(volume=pipette_channel_cells.cells_volume,
                    source=[cells_plate.wells_by_name()[well] for well in pipette_channel_cells.cells_well], # transfer from the specified well in the resevoir containing competent cells
                    dest=[transformation_plate.wells_by_name()[well] for well in pipette_channel_cells.transformation_well], # transfer to transformation plate in the thermocycler
                    new_tip = "once",
                    mix_before=(1,pipette_cells.max_volume)) # Resuspend the competent cells once before transferring into the transformation plate 

    ### DNA TRANSFER ###
    for i in zip(pipette_channel_dna.dna_well, pipette_channel_dna.transformation_well, pipette_channel_dna.dna_volume, pipette_channel_dna.cells_volume):
        pipette_dna.pick_up_tip()
        pipette_dna.aspirate(volume=i[2], location=dna_plate.wells_by_name()[i[0]])
        pipette_dna.dispense(volume=i[2], location=transformation_plate.wells_by_name()[i[1]])
        mixing_volume = (i[2]+i[3])/2
        pipette_dna.mix(repetitions=2, volume=mixing_volume, location=transformation_plate.wells_by_name()[i[1]], rate=2)
        pipette_dna.blow_out(location=transformation_plate.wells_by_name()[i[1]])
        pipette_dna.move_to(transformation_plate.wells_by_name()[i[1]].bottom()) # To make sure that the droplets from the blow out do not stay on the tip
        pipette_dna.drop_tip()

    ### RECOVERY MEDIUM TRANSFER ###
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