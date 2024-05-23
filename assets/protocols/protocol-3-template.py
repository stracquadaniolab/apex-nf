from opentrons import protocol_api, types
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional
import math
import numpy as np

metadata = {
    "apiLevel": "2.13",
    "protocolName": "Protocol 3 - Colony Sampling",
    "description": "OT-2 protocol for colony sampling from agar plates.",
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
    
    protocol_data = namedtuple("protocol_data", ["id","agar_plate_location","agar_plate_weight","media_source_well","sampling_source_well","media_volume","destination_well"])
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

def agar_height(agar_plate_weight: float, empty_agar_plate_weight: float , agar_plate_area: float, agar_density: float) -> float:
    """
    Calculate the the agar height based on the base area of the plate, weight of the empty plate, the weight of plate with agar and the agar density.
    """
    agar_weight = float(agar_plate_weight) - float(empty_agar_plate_weight)
    agar_height = agar_weight/(agar_plate_area*agar_density) # Agar height calculation
    height = agar_height # Adds spotting_height i.e. how many mm below or above the agar the robot should dispense
    return height

def calculate_spiral_coords(max_radius: float, num_points: int = 25, total_rotations: float = 3) -> tuple:  
    """
    Calculate the coordinates for a spiral sampling method.
    
    max_radius (float): The maximum radial distance from the center to the outermost point of the spiral.
    num_points (int): Number of points in the spiral. Defines the granularity of the spiral curve.
    total_rotations (float): Total number of complete 360-degree rotations the spiral will make.

    """
    b = max_radius / (total_rotations * 2 * np.pi) # Calculate the increment factor b based on the max radius and total rotations
    end_theta = total_rotations * 2 * np.pi # Maximum theta based on total rotations
    theta = np.linspace(0, end_theta, num_points) # Create theta values from 0 to end_theta evenly spaced based on num_points
    r = b * theta # Calculate the radius for each theta
    # Calculate x and y coordinates using the radius and theta values
    x = r * np.cos(theta)
    y = r * np.sin(theta)

    return x, y

def run(protocol: protocol_api.ProtocolContext):
    """
    Main function for running the protocol.
    """
    json_params = load_experiment_parameters(INPUT_JSON_FILE) # load the parameters from the json file
    single, multi = load_experiment_data(INPUT_CSV_FILE) # load data from the csv file, modified based on the channel of the pipette

    # Load pipettes
    right_pipette_tipracks = [protocol.load_labware(load_name=json_params["right_pipette_tiprack_name"], location=i) for i in json_params["right_pipette_tiprack_slot"]]
    right_pipette = protocol.load_instrument(instrument_name=json_params["right_pipette_name"], mount="right", tip_racks=right_pipette_tipracks)

    left_pipette_tipracks = [protocol.load_labware(load_name=json_params["left_pipette_tiprack_name"], location=i) for i in json_params["left_pipette_tiprack_slot"]]
    left_pipette = protocol.load_instrument(instrument_name=json_params["left_pipette_name"], mount="left", tip_racks=left_pipette_tipracks)

    pipette_media = right_pipette if choose_pipette_volume(single.media_volume) in json_params["right_pipette_name"] else left_pipette # Choose which pipette to use based on volume
    pipette_channel_media = multi if choose_pipette_channel(str(pipette_media)) == 'multi' else single
    pipette_sampling = right_pipette if choose_pipette_volume([10.0]) in json_params["right_pipette_name"] else left_pipette # Choose which pipette to use based on volume
    pipette_channel_sampling = multi if choose_pipette_channel(str(pipette_sampling)) == 'multi' else single

     # Load hardware and labware
    agar_labware = [protocol.load_labware(load_name=json_params["agar_plate_name"],
                                        location=slot,
                                        label=f"Agar Plate {i+1}")
                    for i, slot in enumerate(json_params["agar_plate_slot"])]

    mapping_dict = {int(slot): labware for slot, labware in zip(json_params["agar_plate_slot"], agar_labware)} # Create a mapping dictionary from slot to agar_labware
    agar_plates = [mapping_dict[int(loc)] for loc in pipette_channel_sampling.agar_plate_location if int(loc) in mapping_dict] # Generate agar_plates list with repeating plates

    media_plate = protocol.load_labware(load_name = json_params["media_plate_name"], location = json_params["media_plate_slot"])
    culture_plate = protocol.load_labware(load_name = json_params["culture_plate_name"], location = json_params["culture_plate_slot"])
    
    pipette_media.transfer(volume=pipette_channel_media.media_volume,
                            source=[media_plate.wells_by_name()[well] for well in pipette_channel_media.media_source_well],
                            dest=[culture_plate.wells_by_name()[well] for well in pipette_channel_media.destination_well],
                            new_tip="once")

    if json_params["sampling_method"] == "spiral":
        x_coords, y_coords = calculate_spiral_coords(json_params["spot_radius"])
        for plate, weight, well, culture_well in zip(agar_plates, pipette_channel_sampling.agar_plate_weight, pipette_channel_sampling.sampling_source_well, pipette_channel_sampling.destination_well):
            pipette_sampling.pick_up_tip()
            sampling_height = agar_height(weight, json_params["empty_agar_plate_weight"], json_params["agar_plate_area"], json_params["agar_density"])
            colony_well = plate.wells_by_name()[well]
            for x,y in zip(x_coords, y_coords):
                colony_sampling = colony_well.bottom(z=sampling_height-json_params["agar_stab_depth"]).move(types.Point(x=x, y=y))
                pipette_sampling.move_to(colony_sampling)
            pipette_sampling.move_to(media_plate[culture_well].bottom())
            pipette_sampling.mix(repetitions=3, rate=4) # Inoculation
            pipette_sampling.drop_tip()

    elif json_params["sampling_method"] == "pierce":
        for plate, weight, well, culture_well in zip(agar_plates, pipette_channel_sampling.agar_plate_weight, pipette_channel_sampling.source_well, pipette_channel_sampling.destination_well):
            pipette_sampling.pick_up_tip()
            sampling_height = agar_height(weight, json_params["empty_agar_plate_weight"], json_params["agar_plate_area"], json_params["agar_density"])
            print(sampling_height)
            colony_well = plate.wells_by_name()[well]
            colony_sampling = colony_well.bottom(z=sampling_height-json_params["agar_stab_depth"])
            pipette_sampling.move_to(colony_sampling)
            pipette_sampling.move_to(media_plate[culture_well].bottom())
            pipette_sampling.mix(repetitions=3, rate=4) # Inoculation
            pipette_sampling.drop_tip()