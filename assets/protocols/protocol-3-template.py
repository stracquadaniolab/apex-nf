from opentrons import protocol_api, types
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional
import math
import numpy as np

metadata = {
    "apiLevel": "2.16",
    "protocolName": "Protocol 3: Colony Sampling",
    "description": "OT-2 protocol for colony sampling from agar plates.",
    "author": "Stracquadanio Lab"
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

def load_json_data(json_content: str) -> dict:
    """Load JSON formatted string with experiment parameters."""
    return json.loads(json_content)

def load_csv_data(csv_content: str):
    """Parse CSV content with experiment data."""
    csv_reader = csv.DictReader(csv_content.splitlines()[1:])
    data = {key: [] for key in csv_reader.fieldnames if key}
    for row in csv_reader:
        for key, value in row.items():
            data[key].append(float(value) if "volume" in key else value)
    return namedtuple("ProtocolData", data.keys())(*[data[key] for key in data.keys()])

def filter_compatible_data(pipette, sources: List[str], volumes: List[float], destinations: List[str], locations: List[any] = None) -> Tuple[List[str], List[float], List[str], List[float]]:
    """Filters sources, volumes, and destinations, optionally handling locations."""
    seen_columns, filtered_sources, filtered_volumes, filtered_destinations, filtered_locations = set(), [], [], [], []
    is_multi_channel = "8-Channel" in str(pipette)

    for i, (source, destination) in enumerate(zip(sources, destinations)):
        formatted_destination = "A" + destination[1:] if is_multi_channel else destination
        formatted_source = "A" + source[1:] if is_multi_channel else source

        if formatted_destination not in seen_columns:
            seen_columns.add(formatted_destination)
            filtered_sources.append(formatted_source)
            filtered_destinations.append(formatted_destination)
            
            if volumes:
                filtered_volumes.append(volumes[i])
            if locations:
                filtered_locations.append(int(locations[i]))
    if locations:
        return filtered_sources, filtered_destinations, filtered_locations
    else:
        return filtered_sources, filtered_volumes, filtered_destinations
    
def setup_pipettes(protocol: protocol_api.ProtocolContext, pipette_info: Dict[str, Any]) -> Dict[str, protocol_api.InstrumentContext]:
    """Load specified pipettes into the protocol based on configuration details provided."""
    available_pipettes = {}
    for side in ["right", "left"]:
        if pipette_info[f"{side}_pipette_name"] != "NA":
            tip_racks = [protocol.load_labware(pipette_info[f"{side}_pipette_tiprack_name"], slot) for slot in pipette_info[f"{side}_pipette_tiprack_slot"]]
            pipette = protocol.load_instrument(pipette_info[f"{side}_pipette_name"], mount=side, tip_racks=tip_racks)
            available_pipettes[pipette_info[f"{side}_pipette_name"]] = pipette
    return available_pipettes

def select_pipette(
    volume: List[float],
    available_pipettes: Dict[str, protocol_api.InstrumentContext],
    is_distribution: bool = False,
    source_to_volumes_map: Dict = None,
) -> protocol_api.InstrumentContext:
    """Determine the appropriate pipette based on the volume and available pipettes."""
    if len(available_pipettes) == 1:
        return next(iter(available_pipettes.values()))
    if is_distribution and source_to_volumes_map:
        max_aspirate_volume = max(
            sum(volumes) for volumes in source_to_volumes_map.values()
        )
        if max_aspirate_volume <= 20:
            pipette_type = "p20"
        elif max_aspirate_volume <= 300:
            pipette_type = "p300"
        else:
            pipette_type = "p1000"
    else:
        min_volume = min(volume)
        if min_volume <= 20:
            pipette_type = "p20"
        elif min_volume <= 300:
            pipette_type = "p300"
        else:
            pipette_type = "p1000"
    fallback_order = {
        "p1000": ["p1000", "p300", "p20"],
        "p300": ["p300", "p1000", "p20"],
        "p20": ["p20", "p300", "p1000"],
    }
    for type_to_try in fallback_order[pipette_type]:
        for pipette_name, pipette in available_pipettes.items():
            if type_to_try in pipette_name:
                return pipette
    return None
    
def agar_height(agar_plate_weight: float, empty_agar_plate_weight: float, agar_plate_area: float, agar_density: float, agar_pierce_depth: float) -> float:
    """Calculate the the agar height based on the base area of the plate, weight of the empty plate, the weight of plate with agar and the agar density."""
    agar_weight = float(agar_plate_weight) - float(empty_agar_plate_weight)
    agar_height = agar_weight/(agar_plate_area*(agar_density/1000))
    height = agar_height + agar_pierce_depth
    return height

def calculate_spiral_coords(max_radius: float, num_points: int = 25, total_rotations: float = 3) -> tuple:  
    """
    Calculate the coordinates for a spiral sampling method.
    max_radius (float): The maximum radial distance from the center to the outermost point of the spiral.
    num_points (int): Number of points in the spiral. Defines the granularity of the spiral curve.
    total_rotations (float): Total number of complete 360-degree rotations the spiral will make.
    """
    b = max_radius / (total_rotations * 2 * np.pi) 
    end_theta = total_rotations * 2 * np.pi
    theta = np.linspace(0, end_theta, num_points)
    r = b * theta
    x = r * np.cos(theta)
    y = r * np.sin(theta)

    return x, y

def run(protocol: protocol_api.ProtocolContext):
    """Main function for running the protocol."""
    json_params = load_json_data(INPUT_JSON_FILE)
    data = load_csv_data(INPUT_CSV_FILE)
    protocol.set_rail_lights(True)

    available_pipettes = setup_pipettes(protocol, json_params)
    pipette_sampling = select_pipette([1], available_pipettes)

    media_distribution_map = defaultdict(list)
    source_well_volumes = {}
    for src, vol in zip(data.media_source_well, data.media_volume):
        if src not in source_well_volumes:
            source_well_volumes[src] = []
        source_well_volumes[src].append(vol)
    pipette_media = select_pipette(
        data.media_volume,
        available_pipettes,
        is_distribution=True,
        source_to_volumes_map=source_well_volumes,
    )

    media_plate = protocol.load_labware(load_name = json_params["media_plate_name"], location = json_params["media_plate_slot"])
    destination_plate = protocol.load_labware(load_name = json_params["destination_plate_name"], location = json_params["destination_plate_slot"])
    
    colony_wells, sampling_destination_wells, locations = filter_compatible_data(pipette_sampling, data.colony_source_well, [], data.destination_well, data.agar_plate_location)
    
    agar_labware = {int(slot): protocol.load_labware(load_name=json_params["agar_plate_name"], location=slot, label=f"Agar Plate {i+1}")
                    for i, slot in enumerate(json_params["agar_plate_slot"])}
    agar_info = {slot: {"empty_plate_weight": weight, "agar_plate_weight": agar_weight}
                 for slot, weight, agar_weight in zip(json_params["agar_plate_slot"], json_params["empty_agar_plate_weight"], json_params["agar_plate_weight"])}
    agar_plates = [agar_labware[loc] for loc in locations]
    empty_plate_weight = [agar_info[loc]["empty_plate_weight"] for loc in locations if loc in agar_info]
    agar_plate_weight = [agar_info[loc]["agar_plate_weight"] for loc in locations if loc in agar_info]
    
    ########## DISTRIBUTE MEDIA ##########
    protocol.comment("Distribute media.")
    media_source, media_volume, media_destination = filter_compatible_data(
        pipette_media, data.media_source_well, data.media_volume, data.destination_well
    )
    for src, vol, dest in zip(media_source, media_volume, media_destination):
        media_distribution_map[src].append((vol, dest))

    pipette_media.pick_up_tip()
    for src, volume_destination_pairs in media_distribution_map.items():
        volumes = [pair[0] for pair in volume_destination_pairs]
        destinations = [pair[1] for pair in volume_destination_pairs]

        pipette_media.distribute(
            volume=volumes,
            source=media_plate.wells_by_name()[src],
            dest=[destination_plate.wells_by_name()[well] for well in destinations],
            new_tip="never",
            blow_out=True,
            blowout_location="source well",
        )
    pipette_media.drop_tip()

    ########## SAMPLING ##########
    protocol.comment("Start sampling cells.")
    for plate, source, destination, empty_weight, agar_weight in zip(agar_plates, colony_wells, sampling_destination_wells, empty_plate_weight, agar_plate_weight):
        pipette_sampling.pick_up_tip()
        sampling_height = agar_height(agar_weight, empty_weight, json_params["agar_plate_area"], json_params["agar_density"], json_params["agar_pierce_depth"])
        colony_well = plate.wells_by_name()[source]
        if json_params["sampling_method"] == "spiral":
            x_coords, y_coords = calculate_spiral_coords(json_params["spot_radius"])
            for x, y in zip(x_coords, y_coords):
                colony_sampling = colony_well.bottom(z=sampling_height).move(types.Point(x=x, y=y))
                pipette_sampling.move_to(location=colony_sampling, speed=50)
        elif json_params["sampling_method"] == "pierce":
            colony_sampling = colony_well.bottom(z=sampling_height)
            pipette_sampling.move_to(location=colony_sampling, speed=50)

        pipette_sampling.aspirate(pipette_sampling.max_volume/2, destination_plate.wells_by_name()[destination])
        pipette_sampling.dispense(pipette_sampling.max_volume/2, destination_plate.wells_by_name()[destination])
        pipette_sampling.drop_tip()

    protocol.set_rail_lights(False)