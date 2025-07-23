from opentrons import protocol_api
import csv
import json
from collections import namedtuple
from typing import Tuple, List

metadata = {
    "apiLevel": "2.16",
    "protocolName": "Protocol 2: Colony selection",
    "description": "OT-2 protocol for colony selection via spotting on selective media plates.",
    "author": "Stracquadanio Lab",
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

def filter_compatible_data(
    pipette,
    sources: List[str],
    volumes: List[float],
    destinations: List[str],
    locations: List[str],
    weights: List[str],
) -> Tuple[List[str], List[float], List[str], List[float], List[float]]:
    """Filters sources, volumes, and destinations."""
    seen_columns, filtered = set(), []
    is_multi_channel = "8-Channel" in str(pipette)

    for source, volume, destination, location, weight in zip(
        sources, volumes, destinations, locations, weights
    ):
        formatted_destination = (
            "A" + destination[1:] if is_multi_channel else destination
        )
        destination_location_key = (formatted_destination, location, weight)

        if destination_location_key not in seen_columns:
            seen_columns.add(destination_location_key)
            formatted_source = "A" + source[1:] if is_multi_channel else source
            filtered.append(
                (
                    formatted_source,
                    volume,
                    formatted_destination,
                    int(location),
                    float(weight),
                )
            )

    return zip(*filtered)

def agar_height(
    agar_plate_weight: float,
    empty_agar_plate_weight: float,
    agar_plate_area: float,
    agar_density: float,
    spotting_height: float,
) -> float:
    """Calculate the the agar height based on the base area of the plate, weight of the empty plate, the weight of plate with agar and the agar density."""
    agar_weight = float(agar_plate_weight) - float(empty_agar_plate_weight)
    agar_height = agar_weight / (agar_plate_area * (agar_density))
    height = agar_height + spotting_height
    return height

def run(protocol: protocol_api.ProtocolContext):
    """Main function for running the protocol."""
    params = load_json_data(INPUT_JSON_FILE)
    data = load_csv_data(INPUT_CSV_FILE)
    protocol.set_rail_lights(True)

    pipette_tipracks = [
        protocol.load_labware(load_name=params["tiprack_name"], location=i)
        for i in params["tiprack_slots"]
    ]
    pipette = protocol.load_instrument(
        instrument_name=params["pipette_name"],
        mount=params["pipette_mount"],
        tip_racks=pipette_tipracks,
    )

    thermocycler_mod = protocol.load_module("thermocycler")
    transformation_plate = thermocycler_mod.load_labware(
        params["transformation_plate_name"]
    )
    thermocycler_mod.open_lid()

    source_well, spotting_volume, destination_well, locations, weights = filter_compatible_data(
        pipette,
        data.transformation_source_well,
        data.spotting_volume,
        data.spotting_well,
        data.agar_plate_slot,
        data.agar_plate_weight,
    )
    agar_plate_slots = set(locations)

    agar_labware = {
        int(slot): protocol.load_labware(
            load_name=params["agar_plate_name"],
            location=slot,
            label=f"Agar Plate {i+1}",
        )
        for i, slot in enumerate(agar_plate_slots)
    }

    agar_info = {}
    for slot, agar_weight in zip(locations, weights):
        if slot not in agar_info:
            agar_info[slot] = {
                "empty_plate_weight": params["empty_agar_plate_weight"],
                "agar_plate_weight": agar_weight,
            }

    agar_plates = [agar_labware[loc] for loc in locations]
    empty_plate_weight = [
        agar_info[loc]["empty_plate_weight"] for loc in locations if loc in agar_info
    ]
    agar_plate_weight = [
        agar_info[loc]["agar_plate_weight"] for loc in locations if loc in agar_info
    ]

    ######## SPOTTING ##########
    pipette.flow_rate.aspirate = 22.6
    pipette.flow_rate.dispense = 22.6
    pipette.flow_rate.blow_out = 22.6
    protocol.comment("Start spotting transformed cells onto the plate(s).")
    for plate, source, volume, destination, empty_weight, agar_weight in zip(
        agar_plates,
        source_well,
        spotting_volume,
        destination_well,
        empty_plate_weight,
        agar_plate_weight,
    ):
        pipette.pick_up_tip()
        pipette.well_bottom_clearance.dispense = 1
        if "|" in destination:
            destinations = destination.split("|")
            pipette.mix(
                repetitions=3,
                volume=params["mixing_volume"],
                location=transformation_plate[source]
            )
            for dest in destinations:
                pipette.aspirate(
                    volume=volume + params["additional_volume"],
                    location=transformation_plate[source]
                )
                pipette.well_bottom_clearance.dispense = agar_height(
                    agar_weight,
                    empty_weight,
                    params["agar_plate_area"],
                    params["agar_density"],
                    params["spotting_height"],
                )
                pipette.dispense(volume=volume, location=plate[dest])
                protocol.delay(seconds=5)
            pipette.drop_tip()
        else:
            pipette.mix(
                repetitions=3,
                volume=params["mixing_volume"],
                location=transformation_plate[source]
            )
            pipette.aspirate(
                volume=volume + params["additional_volume"],
                location=transformation_plate[source]
            )
            pipette.well_bottom_clearance.dispense = agar_height(
                agar_weight,
                empty_weight,
                params["agar_plate_area"],
                params["agar_density"],
                params["spotting_height"],
            )
            pipette.dispense(volume=volume, location=plate[destination])
            protocol.delay(seconds=5)
            pipette.drop_tip()

    protocol.set_rail_lights(False)
    protocol.comment("Protocol successfully completed.")
