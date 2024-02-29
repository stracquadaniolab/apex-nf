from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional
import math

metadata = {
    "apiLevel": "2.13",
    "protocolName": "Agar plate spotting",
    "description": "OT-2 rotocol for agar plate spotting.",
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
    This function parses the csv file with the data for the experiment and returns them as namedtuples.
    """
    csv_data = csv.DictReader(csv_file.splitlines())

    single_channel_wells = [] # List of wells when single channel pipette is used
    multi_channel_wells = [] # List of wells when multi channel pipette is used
    columns = defaultdict(str)

    for row in csv_data:
        single_channel_wells.append(row) # For single channel the list of wells stays as provided in the csv file
        well = row["source_well"]
        row_letter, column_number = well[0], well[1:] # Well annotation is in the form "A1"
        if not columns[column_number]:
            multi_channel_wells.append(row) # For multi channel the list is modified so only the first well of a column is kept
            columns[column_number] = row_letter
    
    protocol_data = namedtuple("protocol_data", ["ID", "location", "source_well", "destination_well", "spotting_volume", "agar_plate_weight"])
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

def agar_height(agar_plate_weight: float, plate_weight_without_agar: float , agar_plate_shape: str, agar_plate_dimensions: list, agar_density: float, spotting_height: float) -> float:
    """
    Calculate the the agar height based on the shape of the plate, weight of the plate itself, the weight of plate with agar and the agar density.
    """
    if agar_plate_shape == "circular":
        bottom_area = math.pi*(agar_plate_dimensions[0]/2)**2 # For circular petri dish
    elif agar_plate_shape == "rectangular":
        bottom_area = agar_plate_dimensions[0]*agar_plate_dimensions[1] # For rectangular one well plate
    else:
        print("Invalid plate shape.")

    agar_weight = float(agar_plate_weight) - float(plate_weight_without_agar)
    agar_height = agar_weight/(bottom_area*agar_density) # Agar height calculation
    spotting_height = agar_height + spotting_height # Adds spotting_height ie. how many mm above the agar the robot should pipette
    return spotting_height

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
    agar_plates = [protocol.load_labware(load_name=json_params["agar_plate_name"],
                                         location=slot,
                                         label=f"Agar Plate {str(i+1)}")
                                         for i, slot in enumerate(pipette_channel.location)]
    
    if json_params["transformation_plate_slot"] == "thermocycler":
        thermocycler_mod = protocol.load_module("thermocycler") # Thermocycler module, takes location 7,8,10,11
        transformation_plate = thermocycler_mod.load_labware(json_params["transformation_plate_name"])
        thermocycler_mod.open_lid()
    else:
        transformation_plate = protocol.load_labware(load_name=json_params["transformation_plate_name"], location=json_params["transformation_plate_slot"])

    thermocycler_mod = protocol.load_module("thermocycler") # Thermocycler module, takes location 7,8,10,11
    transformation_plate = thermocycler_mod.load_labware(json_params["transformation_plate_name"]) # Transformation done using a thermocycler
    
    ######## SPOTTING ##########
    thermocycler_mod.open_lid()
    for plate, source, destination, volume, weight in zip(agar_plates, pipette_channel.source_wells, pipette_channel.destination_wells, pipette_channel.spotting_volume, pipette_channel.agar_plate_weight):
        pipette.well_bottom_clearance.dispense = 1 # Reset the dispense height 
        pipette.pick_up_tip()
        pipette.mix(repetitions=3, volume=pipette.max_volume, location=transformation_plate[source], rate=2) # Resuspend the transformed cells
        pipette.aspirate(volume=volume + json_params["dead_volume"], location=transformation_plate[source], rate=2) # Aspirate the spotting volume and dead volume for better accuracy
        pipette.well_bottom_clearance.dispense = agar_height(weight, json_params["plate_weight_without_agar"], json_params["agar_plate_shape"], json_params["agar_plate_dimensions"], json_params["agar_density"], json_params["spotting_height"]) #Adjust height to the agar wight
        pipette.dispense(volume=volume, location=plate[destination], rate=4) # Spotting
        protocol.delay(seconds=5) # Weight in case there is a problem with a droplet forming
        pipette.drop_tip()