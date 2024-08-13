from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional

metadata = {
    "apiLevel": "2.15",
    "protocolName": "Protocol 4: Protein Expression Induction",
    "description": "OT-2 protocol for protein expression indcution.",
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
    
def load_or_reuse_labware(protocol: protocol_api.ProtocolContext, plate_info: Dict[str, str], loaded_plates: Dict[str, protocol_api.Labware]):
    """Load a plate into the protocol or reuse an existing one if the slot is already occupied."""    
    slot = plate_info["slot"]
    return loaded_plates[slot] if slot in loaded_plates else loaded_plates.setdefault(slot, protocol.load_labware(plate_info["name"], slot))

def filter_data(pipette, sources: List[str], volumes: List[float], destinations: List[str]) -> Tuple[List[str], List[float], List[str]]:
    """Filters out sources, volumes, and destinations. Adjusts wells to start with "A" for 8-channel pipettes, unless source is "NA".
    Leaves data unmodified for single-channel pipettes."""
    seen_columns, filtered_sources, filtered_volumes, filtered_destinations = set(), [], [], []
    is_multi_channel = "8-Channel" in str(pipette)
    
    for source, volume, destination in zip(sources, volumes, destinations):
        if source == "NA" or (formatted_destination := "A" + destination[1:] if is_multi_channel else destination) in seen_columns:
            continue
        
        seen_columns.add(formatted_destination)
        formatted_source = "A" + source[1:] if is_multi_channel and source != "NA" else source
        filtered_sources.append(formatted_source)
        filtered_volumes.append(volume)
        filtered_destinations.append(formatted_destination)
    
    return filtered_sources, filtered_volumes, filtered_destinations

def setup_pipettes(protocol: protocol_api.ProtocolContext, pipette_info: Dict[str, Any]) -> Dict[str, protocol_api.InstrumentContext]:
    """Load specified pipettes into the protocol based on configuration details provided."""
    loaded_pipettes = {}
    for side in ["right", "left"]:
        if pipette_info[f"{side}_pipette_name"] != "NA":
            tip_racks = [protocol.load_labware(pipette_info[f"{side}_pipette_tiprack_name"], slot) for slot in pipette_info[f"{side}_pipette_tiprack_slot"]]
            pipette = protocol.load_instrument(pipette_info[f"{side}_pipette_name"], mount=side, tip_racks=tip_racks)
            loaded_pipettes[pipette_info[f"{side}_pipette_name"]] = pipette
    return loaded_pipettes

def select_pipette(volume: List[float], loaded_pipettes: Dict[str, protocol_api.InstrumentContext]) -> protocol_api.InstrumentContext:
    """ Determine the appropriate pipette based on the volume and available pipettes. """
    if len(loaded_pipettes) == 1:
        return next(iter(loaded_pipettes.values()))
    pipette_type = "p20" if min(volume, default=float("inf")) <= 20 else "p300"
    for pipette_name, pipette in loaded_pipettes.items():
        if pipette_type in pipette_name:
            return pipette
    return None

def run(protocol: protocol_api.ProtocolContext):
    """Main function for running the protocol."""
    json_params = load_json_data(INPUT_JSON_FILE)
    csv_data = load_csv_data(INPUT_CSV_FILE)
    protocol.set_rail_lights(True)
    
    loaded_pipettes = setup_pipettes(protocol, json_params)
    pipette_media = select_pipette(csv_data.media_volume, loaded_pipettes)
    pipette_culture = select_pipette(csv_data.culture_volume, loaded_pipettes)
    pipette_inducer = select_pipette(csv_data.inducer_volume, loaded_pipettes)
    
    loaded_plates = {}
    media_plate = load_or_reuse_labware(protocol, {"name": json_params["media_plate_name"], "slot": json_params["media_plate_slot"]}, loaded_plates)
    culture_plate = load_or_reuse_labware(protocol, {"name": json_params["culture_plate_name"], "slot": json_params["culture_plate_slot"]}, loaded_plates)
    inducer_plate = load_or_reuse_labware(protocol, {"name": json_params["inducer_plate_name"], "slot": json_params["inducer_plate_slot"]}, loaded_plates)
    destination_plate = load_or_reuse_labware(protocol, {"name": json_params["destination_plate_name"], "slot": json_params["destination_plate_slot"]}, loaded_plates)

    ########## DISTRIBUTE MEDIA ##########
    media_wells, media_volumes, media_destination_wells = filter_data(pipette_media, csv_data.media_well, csv_data.media_volume, csv_data.destination_well)
    pipette_media.transfer(volume=media_volumes,
                            source=[media_plate.wells_by_name()[well] for well in media_wells],
                            dest=[destination_plate.wells_by_name()[well] for well in media_destination_wells],
                            new_tip="once")

    ########## CULTURE TRANSFER ##########
    culture_wells, culture_volumes, culture_destination_wells = filter_data(pipette_culture, csv_data.culture_well, csv_data.culture_volume, csv_data.destination_well)
    pipette_culture.transfer(
        volume=culture_volumes,
        source=[culture_plate.wells_by_name()[well] for well in culture_wells],
        dest=[destination_plate.wells_by_name()[well] for well in culture_destination_wells],
        mix_before=(2, 20),
        mix_after=(1, 20),
        new_tip="always"
    )

    protocol.pause("Incubate the culture plate with shaking untill it reaches the desired growth phase and click 'resume'.")

    ########## INDUCER TRANSFER ##########
    inducer_wells, inducer_volumes, inducer_destination_wells = filter_data(pipette_inducer, csv_data.inducer_well, csv_data.inducer_volume, csv_data.destination_well)
    pipette_inducer.transfer(
        volume=inducer_volumes,
        source=[inducer_plate.wells_by_name()[well] for well in inducer_wells],
        dest=[destination_plate.wells_by_name()[well] for well in inducer_destination_wells],
        mix_after=(1, 20),
        new_tip="always",
    )
    protocol.set_rail_lights(False)
