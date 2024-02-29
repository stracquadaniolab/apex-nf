csv_data = """ID,agar_plate_location,source_well,destination_well,media_volume,agar_plate_weight
water-BL21,1,A1,A1,1500,76.32
pUC19-BL21,1,B1,B1,1500,76.32
pJKR-BL21,1,C1,C1,1500,76.32
pJKR-BL21,1,D1,D1,1500,76.32
pJKR-BL21,1,E1,E1,1500,76.32
pJKR-BL21,1,F1,F1,1500,76.32
pJKR-BL21,1,G1,G1,1500,76.32
pJKR-BL21,1,H1,H1,1500,76.32
water-BL21,1,A2,A2,1500,76.32
pUC19-BL21,1,B2,B2,1500,76.32
pJKR-BL21,1,C2,C2,1500,76.32
pJKR-BL21,1,D2,D2,1500,76.32
pJKR-BL21,1,E2,E2,1500,76.32
pJKR-BL21,1,F2,F2,1500,76.32
pJKR-BL21,1,G2,G2,1500,76.32
pJKR-BL21,1,H2,H2,1500,76.32
water-BL21,1,A3,A3,1500,76.32
pUC19-BL21,1,B3,B3,1500,76.32
pJKR-BL21,1,C3,C3,1500,76.32
pJKR-BL21,1,D3,D3,1500,76.32
pJKR-BL21,1,E3,E3,1500,76.32
pJKR-BL21,1,F3,F3,1500,76.32
pJKR-BL21,1,G3,G3,1500,76.32
pJKR-BL21,1,H3,H3,1500,76.32"""

json_parameters = """{
    "pipette_tiprack_name":"opentrons_96_tiprack_20ul",
    "pipette_tiprack_slot":[5,6],
    "pipette_name":"p20_multi_gen2",
    "pipette_mount":"left",
    "media_plate_name":"usascientific_96_wellplate_2.4ml_deep",
    "media_plate_slot":2,
    "agar_plate_name":"nunc96grid_96_wellplate_10ul",
    "agar_plate_slot": [1],
    "agar_plate_shape":"rectangular",
    "agar_plate_dimensions":[127.8,85.5],
    "plate_weight_without_agar":38.92,
    "agar_density":0.00095,
    "agar_stab_depth":0
}"""

from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional
import math

metadata = {
    "apiLevel": "2.13",
    "protocolName": "Colony picking",
    "description": "OT-2 protocol for colony picking from agar plates.",
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
    media_plate = protocol.load_labware(load_name=json_params["media_plate_name"], location=json_params["media_plate_slot"])

    ######## COLONY PICKING ##########
    for plate, source, destination, weight in zip(agar_plates, pipette_channel.source_wells, pipette_channel.destination_wells, pipette_channel.agar_plate_weight):
        pipette.pick_up_tip()
        picking_height = agar_height(weight, json_params["plate_weight_without_agar"], json_params["agar_plate_shape"], json_params["agar_plate_dimensions"], json_params["agar_density"], json_params["spotting_height"]) - json_params["agar_stab_depth"] # Adjust height to the agar weight
        pipette.move_to(plate[source].bottom(z=picking_height))
        pipette.move_to(media_plate[destination].bottom())
        pipette.mix(repetitions=3, rate=4) # Inoculation
        pipette.drop_tip()