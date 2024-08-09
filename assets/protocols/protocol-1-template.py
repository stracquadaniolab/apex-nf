from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional

metadata = {
    "apiLevel": "2.15",
    "protocolName": "Protocol 1: E. coli heat shock transformation",
    "description": "OT-2 protocol for standard E. coli heat shock transformation using thermocycler.",
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
            data[key].append(float(value) if 'volume' in key else value)
    return namedtuple('ProtocolData', data.keys())(*[data[key] for key in data.keys()])
    
def load_or_reuse_labware(protocol: protocol_api.ProtocolContext, plate_info: Dict[str, str], loaded_plates: Dict[str, protocol_api.Labware]):
    """Load a plate into the protocol or reuse an existing one if the slot is already occupied."""    
    slot = plate_info["slot"]
    return loaded_plates[slot] if slot in loaded_plates else loaded_plates.setdefault(slot, protocol.load_labware(plate_info["name"], slot))

def filter_and_transfer(pipette, sources: List[str], volumes: List[float], destinations: List[str]) -> Tuple[List[str], List[float], List[str]]:
    """Filters out sources, volumes, and destinations. Adjusts wells to start with 'A' for 8-channel pipettes."""
    seen_columns, filtered_sources, filtered_volumes, filtered_destinations = set(), [], [], []
    is_multi_channel = "8-Channel" in str(pipette)
    
    for source, volume, destination in zip(sources, volumes, destinations):
        destination_column = destination[1:]
        formatted_destination = 'A' + destination_column if is_multi_channel else destination
        formatted_source = 'A' + source[1:] if is_multi_channel else source

        if formatted_destination in seen_columns:
            continue

        seen_columns.add(formatted_destination)
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
    pipette_type = "p20" if min(volume, default=float('inf')) <= 20 else "p300"
    for pipette_name, pipette in loaded_pipettes.items():
        if pipette_type in pipette_name:
            return pipette
    return None

def run(protocol: protocol_api.ProtocolContext):
    """Main function for running the protocol."""
    json_params = load_json_data(INPUT_JSON_FILE)
    data = load_csv_data(INPUT_CSV_FILE)
    loaded_pipettes = setup_pipettes(protocol, json_params)

    pipette_cells = select_pipette(data.cells_volume, loaded_pipettes)
    pipette_dna = select_pipette(data.dna_volume, loaded_pipettes)
    pipette_media = select_pipette(data.media_volume, loaded_pipettes)

    loaded_plates = {}
    cells_plate = load_or_reuse_labware(protocol, {"name": json_params["cells_plate_name"], "slot": json_params["cells_plate_slot"]}, loaded_plates)
    dna_plate = load_or_reuse_labware(protocol, {"name": json_params["dna_plate_name"], "slot": json_params["dna_plate_slot"]}, loaded_plates)
    media_plate = load_or_reuse_labware(protocol, {"name": json_params["media_plate_name"], "slot": json_params["media_plate_slot"]}, loaded_plates)
    
    protocol.set_rail_lights(True)

    if json_params["destination_plate_slot"] ==  "thermocycler":
        thermocycler_mod = protocol.load_module("thermocycler")
        destination_plate = thermocycler_mod.load_labware(json_params["destination_plate_name"])
        thermocycler_mod.set_block_temperature(temperature=json_params["pre_shock_incubation_temp"])
        thermocycler_mod.open_lid()
        protocol.pause("Put plate into the thermocycler module and click 'resume'.")
    else:
        destination_plate = protocol.load_labware(json_params["destination_plate_name"], json_params["destination_plate_slot"])

    ########## ADD COMPETENT CELLS ##########
    protocol.comment("Adding competent cells.")
    pipette_cells.pick_up_tip()
    mixed_wells = set()
    cells_source, cells_volume, cells_destination = filter_and_transfer(pipette_cells, data.cells_well, data.cells_volume, data.destination_well)
    print(data.cells_well, data.cells_volume, data.destination_well)
    print(cells_source, cells_volume, cells_destination)
    
    cumulative_cell_volumes = defaultdict(float)
    for src_well, vol_cells in zip(cells_source, cells_volume):
        cumulative_cell_volumes[src_well] += vol_cells

    for src_well, vol_cells, dest_well in zip(cells_source, cells_volume, cells_destination):
        if src_well not in mixed_wells:
            mix_volume = cumulative_cell_volumes[src_well]
            if mix_volume > pipette_cells.max_volume:
                mix_volume = pipette_cells.max_volume
            pipette_cells.mix(1, mix_volume, cells_plate.wells_by_name()[src_well])
            mixed_wells.add(src_well)

        pipette_cells.transfer(volume=vol_cells,
                                source=cells_plate.wells_by_name()[src_well],
                                dest=destination_plate.wells_by_name()[dest_well],
                                new_tip="never")
    pipette_cells.drop_tip()

    ########## ADD DNA ##########
    protocol.comment("Adding DNA.")
    dna_source, dna_volume, dna_destination = filter_and_transfer(pipette_dna, data.dna_well, data.dna_volume, data.destination_well,)
    for src_well, vol_dna, dest_well, vol_cells in zip(dna_source, dna_volume, dna_destination, cells_volume):
        pipette_dna.pick_up_tip()
        pipette_dna.aspirate(volume=vol_dna, location=dna_plate.wells_by_name()[src_well])
        pipette_dna.dispense(volume=vol_dna, location=destination_plate.wells_by_name()[dest_well])
        mixing_volume = (vol_dna + vol_cells) / 2
        pipette_dna.mix(repetitions=2, volume=mixing_volume, location=destination_plate.wells_by_name()[dest_well])
        pipette_dna.blow_out(location=destination_plate.wells_by_name()[dest_well])
        pipette_dna.move_to(destination_plate.wells_by_name()[dest_well].bottom()) # To make sure that the droplets from the blow out do not stay on the tip
        pipette_dna.drop_tip()

    ########## HEAT SHOCK TRANSFORMATION ##########
    if json_params["destination_plate_slot"] ==  "thermocycler":
        thermocycler_mod.close_lid()
        thermocycler_mod.set_block_temperature(temperature=json_params["pre_shock_incubation_temp"], 
                                            hold_time_minutes=json_params["pre_shock_incubation_time"])
        protocol.comment("Starting heat shock transformation.")
        thermocycler_mod.set_block_temperature(temperature=json_params["heat_shock_temp"], 
                                            hold_time_seconds=json_params["heat_shock_time"])
        thermocycler_mod.set_block_temperature(temperature=json_params["post_shock_incubation_temp"],
                                            hold_time_minutes=json_params["post_shock_incubation_time"])
        thermocycler_mod.open_lid()
    else:
        protocol.pause("Put plate into an external thermocycler for heat-shock transformation and return.")

    ######## ADD RECOVERY MEDIUM ##########
    protocol.comment("Adding recovery media.")
    media_source, media_volume, media_destination = filter_and_transfer(pipette_media, data.media_well, data.media_volume, data.destination_well)
    for src_well, vol_media, dest_well, vol_cells in zip(media_source, media_volume, media_destination, cells_volume):
        pipette_media.pick_up_tip()
        pipette_media.aspirate(volume=vol_media + vol_cells, location=media_plate.wells_by_name()[src_well])
        pipette_media.dispense(volume=vol_media, location=destination_plate.wells_by_name()[dest_well])
        for _ in range(2):
            pipette_media.aspirate(volume=(vol_media + vol_cells) / 2, location=destination_plate.wells_by_name()[dest_well])
            pipette_media.dispense(volume=(vol_media + vol_cells) / 2, location=destination_plate.wells_by_name()[dest_well])
        pipette_media.blow_out(location=destination_plate.wells_by_name()[dest_well])
        pipette_media.move_to(destination_plate.wells_by_name()[dest_well].bottom())
        pipette_media.drop_tip()
    
    ######## RECOVERY INCUBATION ##########
    if json_params["destination_plate_slot"] ==  "thermocycler":
        thermocycler_mod.close_lid()
        thermocycler_mod.set_lid_temperature(temperature=json_params["recovery_temp"])
        thermocycler_mod.set_block_temperature(temperature=json_params["recovery_temp"], 
                                            hold_time_minutes=json_params["recovery_time"])
        thermocycler_mod.deactivate_lid()
        thermocycler_mod.deactivate()
        protocol.set_rail_lights(False)
    else:
        protocol.comment("Put plate into an external thermocycler for incubation.")

    protocol.set_rail_lights(False)