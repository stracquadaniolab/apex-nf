from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, Any

metadata = {
    "apiLevel": "2.16",
    "protocolName": "Protocol 1: Heat shock transformation",
    "description": "OT-2 protocol for standard E. coli heat shock transformation using Opentrons thermocycler.",
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
    
def load_or_reuse_labware(protocol: protocol_api.ProtocolContext, plate_info: Dict[str, str], loaded_plates: Dict[str, protocol_api.Labware]):
    """Load a plate into the protocol or reuse an existing one if the slot is already occupied."""    
    slot = plate_info["slot"]
    return loaded_plates[slot] if slot in loaded_plates else loaded_plates.setdefault(slot, protocol.load_labware(plate_info["name"], slot))

def filter_compatible_data(pipette, sources: List[str], volumes: List[float], destinations: List[str]) -> Tuple[List[str], List[float], List[str]]:
    """Filters out "NA" sources and adjusts well identifiers for 8-channel pipettes."""
    seen_columns, filtered = set(), []
    is_multi_channel = "8-Channel" in str(pipette)

    for src, vol, dest in zip(sources, volumes, destinations):
        if src == "NA" or ("A" + dest[1:] if is_multi_channel else dest) in seen_columns:
            continue

        formatted_dest = "A" + dest[1:] if is_multi_channel else dest
        seen_columns.add(formatted_dest)
        filtered.append(("A" + src[1:] if is_multi_channel else src, vol, formatted_dest))

    return zip(*filtered)

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

def run(protocol: protocol_api.ProtocolContext):
    """Main function for running the protocol."""
    params = load_json_data(INPUT_JSON_FILE)
    data = load_csv_data(INPUT_CSV_FILE)
    protocol.set_rail_lights(True)

    available_pipettes = setup_pipettes(protocol, params)
    pipette_dna = select_pipette(data.dna_volume, available_pipettes)
    pipette_media = select_pipette(data.media_volume, available_pipettes)

    cells_distribution_map = defaultdict(list)
    source_well_volumes = {}
    for src, vol in zip(data.cells_source_well, data.cells_volume):
        if src not in source_well_volumes:
            source_well_volumes[src] = []
        source_well_volumes[src].append(vol)
    pipette_cells = select_pipette(
        data.cells_volume,
        available_pipettes,
        is_distribution=True,
        source_to_volumes_map=source_well_volumes,
    )

    loaded_plates = {}
    cells_plate = load_or_reuse_labware(protocol, {"name": params["cells_plate_name"], "slot": params["cells_plate_slot"]}, loaded_plates)
    dna_plate = load_or_reuse_labware(protocol, {"name": params["dna_plate_name"], "slot": params["dna_plate_slot"]}, loaded_plates)
    media_plate = load_or_reuse_labware(protocol, {"name": params["media_plate_name"], "slot": params["media_plate_slot"]}, loaded_plates)
    
    thermocycler_mod = protocol.load_module("thermocycler")
    transformation_plate = thermocycler_mod.load_labware(params["transformation_plate_name"])
    thermocycler_mod.set_block_temperature(temperature=params["pre_shock_incubation_temp"])
    thermocycler_mod.open_lid()

    ########## DISTRIBUTE COMPETENT CELLS ##########
    protocol.comment("Distributing competent cells.")
    pipette_cells.flow_rate.aspirate = pipette_cells.flow_rate.aspirate / 2
    pipette_cells.flow_rate.dispense = pipette_cells.flow_rate.dispense / 2
    cells_source, cells_volume, cells_destination = filter_compatible_data(pipette_cells, data.cells_source_well, data.cells_volume, data.transformation_well)
    for src, vol, dest in zip(cells_source, cells_volume, cells_destination):
        cells_distribution_map[src].append((vol, dest))

    pipette_cells.pick_up_tip()
    for src, volume_destination_pairs in cells_distribution_map.items():
        volumes = [pair[0] for pair in volume_destination_pairs]
        destinations = [pair[1] for pair in volume_destination_pairs]
        mix_volume = sum(volumes)/2 if sum(volumes)/2 <= pipette_cells.max_volume else pipette_cells.max_volume
        pipette_cells.distribute(
            volume=volumes,
            source=cells_plate.wells_by_name()[src],
            dest=[transformation_plate.wells_by_name()[well] for well in destinations],
            new_tip="never",
            mix_before = (1, mix_volume),
            blow_out=True,
            blowout_location="source well",
        )
    pipette_cells.drop_tip()

    ########## ADD DNA ##########
    protocol.comment("Adding DNA to cells.")
    dna_source, dna_volume, dna_destination = filter_compatible_data(pipette_dna, data.dna_source_well, data.dna_volume, data.transformation_well)
    cells_source, cells_volume, cells_destination = filter_compatible_data(pipette_dna, data.cells_source_well, data.cells_volume, data.transformation_well)
    for src_well, vol_dna, dest_well, vol_cells in zip(dna_source, dna_volume, dna_destination, cells_volume):
        pipette_dna.pick_up_tip()
        pipette_dna.aspirate(volume=vol_dna, location=dna_plate.wells_by_name()[src_well])
        pipette_dna.dispense(volume=vol_dna, location=transformation_plate.wells_by_name()[dest_well])
        mix_volume = (vol_dna + vol_cells) / 2
        mix_volume = mix_volume if mix_volume <= pipette_dna.max_volume / 2 else pipette_dna.max_volume
        pipette_dna.mix(repetitions=2, volume=mix_volume, location=transformation_plate.wells_by_name()[dest_well], rate=0.5)
        pipette_dna.blow_out(location=transformation_plate.wells_by_name()[dest_well])
        pipette_dna.move_to(transformation_plate.wells_by_name()[dest_well].bottom())
        pipette_dna.drop_tip()

    ########## HEAT SHOCK TRANSFORMATION ##########
    protocol.comment("Starting heat shock transformation.")
    max_cells_dna_volume = max([(vol_dna + vol_cells) for vol_dna, vol_cells in zip(dna_volume, cells_volume)])
    thermocycler_mod.close_lid()
    thermocycler_mod.set_block_temperature(temperature=params["pre_shock_incubation_temp"], 
                                            hold_time_minutes=params["pre_shock_incubation_time"],
                                            block_max_volume=max_cells_dna_volume)
    thermocycler_mod.set_block_temperature(temperature=params["heat_shock_temp"], 
                                            hold_time_seconds=params["heat_shock_time"],
                                            block_max_volume=max_cells_dna_volume)
    thermocycler_mod.set_block_temperature(temperature=params["post_shock_incubation_temp"],
                                            hold_time_minutes=params["post_shock_incubation_time"],
                                            block_max_volume=max_cells_dna_volume)
    thermocycler_mod.open_lid()

    ######## ADD RECOVERY MEDIUM ##########
    protocol.comment("Adding recovery media to transformed cells.")
    media_source, media_volume, media_destination = filter_compatible_data(pipette_media, data.media_source_well, data.media_volume, data.transformation_well)
    cells_source, cells_volume, cells_destination = filter_compatible_data(pipette_media, data.cells_source_well, data.cells_volume, data.transformation_well)
    for src_well, vol_media, dest_well, vol_cells in zip(media_source, media_volume, media_destination, cells_volume):
        mix_volume = (vol_media + vol_cells) / 2
        mix_volume = mix_volume if mix_volume <= pipette_media.max_volume / 2 else pipette_media.max_volume
        pipette_media.transfer(volume=vol_media,
                                    source=media_plate.wells_by_name()[src_well],
                                    dest=transformation_plate.wells_by_name()[dest_well],
                                    mix_after=(2, mix_volume),
                                    new_tip="always")

    ######## RECOVERY INCUBATION ##########
    protocol.comment("Starting recovery incubation.")
    max_cells_media_volume = max([(vol_cells + vol_media) for vol_cells, vol_media in zip(cells_volume, media_volume)])
    thermocycler_mod.close_lid()
    thermocycler_mod.set_lid_temperature(temperature=params["recovery_temp"])
    thermocycler_mod.set_block_temperature(temperature=params["recovery_temp"], 
                                            hold_time_minutes=params["recovery_time"],
                                            block_max_volume=max_cells_media_volume)
    thermocycler_mod.deactivate_lid()
    thermocycler_mod.deactivate()
    protocol.set_rail_lights(False)
    protocol.comment("Protocol successfully completed.")