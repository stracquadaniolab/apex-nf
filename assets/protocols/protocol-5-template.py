from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional

metadata = {
    "apiLevel": "2.16",
    "protocolName": "Protocol 5: Colony PCR Sample Preparation",
    "description": "OT-2 protocol for Colony PCR Sample Preparation using Opentrons thermocycler.",
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


def load_or_reuse_labware(
    protocol: protocol_api.ProtocolContext,
    plate_info: Dict[str, str],
    loaded_plates: Dict[str, protocol_api.Labware],
):
    """Load a plate into the protocol or reuse an existing one if the slot is already occupied."""
    slot = plate_info["slot"]
    return (
        loaded_plates[slot]
        if slot in loaded_plates
        else loaded_plates.setdefault(
            slot, protocol.load_labware(plate_info["name"], slot)
        )
    )


def filter_compatible_data(
    pipette, sources: List[str], volumes: List[float], destinations: List[str]
) -> Tuple[List[str], List[float], List[str]]:
    """Filters out "NA" sources and adjusts well identifiers for 8-channel pipettes."""
    seen_columns, filtered = set(), []
    is_multi_channel = "8-Channel" in str(pipette)

    for src, vol, dest in zip(sources, volumes, destinations):
        if (
            src == "NA"
            or ("A" + dest[1:] if is_multi_channel else dest) in seen_columns
        ):
            continue

        formatted_dest = "A" + dest[1:] if is_multi_channel else dest
        seen_columns.add(formatted_dest)
        filtered.append(
            ("A" + src[1:] if is_multi_channel else src, vol, formatted_dest)
        )

    return zip(*filtered)


def setup_pipettes(
    protocol: protocol_api.ProtocolContext, pipette_info: Dict[str, Any]
) -> Dict[str, protocol_api.InstrumentContext]:
    """Load specified pipettes into the protocol based on configuration details provided."""
    available_pipettes = {}
    for side in ["right", "left"]:
        if pipette_info[f"{side}_pipette_name"] != "NA":
            tip_racks = [
                protocol.load_labware(
                    pipette_info[f"{side}_pipette_tiprack_name"], slot
                )
                for slot in pipette_info[f"{side}_pipette_tiprack_slot"]
            ]
            pipette = protocol.load_instrument(
                pipette_info[f"{side}_pipette_name"], mount=side, tip_racks=tip_racks
            )
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
    json_params = load_json_data(INPUT_JSON_FILE)
    data = load_csv_data(INPUT_CSV_FILE)
    protocol.set_rail_lights(True)

    available_pipettes = setup_pipettes(protocol, json_params)

    loaded_plates = {}
    reagent_plate = load_or_reuse_labware(
        protocol,
        {
            "name": json_params["reagent_plate_name"],
            "slot": json_params["reagent_plate_slot"],
        },
        loaded_plates,
    )

    thermocycler_mod = protocol.load_module("thermocycler")
    pcr_plate = thermocycler_mod.load_labware(json_params["pcr_plate_name"])

    thermocycler_mod.open_lid()

    water_distribution_map = defaultdict(list)
    source_well_volumes = {}
    for src, vol in zip(data.water_source_well, data.water_volume):
        if src not in source_well_volumes:
            source_well_volumes[src] = []
        source_well_volumes[src].append(vol)
    water_pipette = select_pipette(
        data.water_volume,
        available_pipettes,
        is_distribution=True,
        source_to_volumes_map=source_well_volumes,
    )

    mastermix_pipette = select_pipette(data.mastermix_volume, available_pipettes)

    ########## DSITRIBUTE WATER ##########
    water_source, water_volume, water_destination = filter_compatible_data(
        water_pipette, data.water_source_well, data.water_volume, data.destination_well
    )
    for src, vol, dest in zip(water_source, water_volume, water_destination):
        water_distribution_map[src].append((vol, dest))

    water_pipette.pick_up_tip()
    for src, volume_destination_pairs in water_distribution_map.items():
        volumes = [pair[0] for pair in volume_destination_pairs]
        destinations = [pair[1] for pair in volume_destination_pairs]

        water_pipette.distribute(
            volume=volumes,
            source=reagent_plate.wells_by_name()[src],
            dest=[pcr_plate.wells_by_name()[well] for well in destinations],
            new_tip="never",
            blow_out=True,
            blowout_location="source well",
        )
    water_pipette.drop_tip()

    ########## MANUAL SINGLE COLONY PICKING AND RESUSPENSION ##########
    protocol.pause(
        "Take the plate, and resuspend the colonies into wells with water. Put the plate into the thermocycler and click 'resume'."
    )

    ########## TRANSFER MASTERMIX ##########
    mastermix_source, mastermix_volume, mastermix_destination = filter_compatible_data(
        mastermix_pipette,
        data.mastermix_source_well,
        data.mastermix_volume,
        data.destination_well,
    )
    water_source, water_volume, water_destination = filter_compatible_data(
        mastermix_pipette,
        data.water_source_well,
        data.water_volume,
        data.destination_well,
    )

    for src, vol_mastermix, vol_water, dest in zip(
        mastermix_source, mastermix_volume, water_volume, mastermix_destination
    ):
        mixing_volume = (vol_water + vol_mastermix) / 2
        mixing_volume = (
            mixing_volume
            if mixing_volume <= mastermix_pipette.max_volume / 2
            else mastermix_pipette.max_volume
        )
        mastermix_pipette.transfer(
            volume=vol_mastermix,
            source=reagent_plate.wells_by_name()[src],
            dest=pcr_plate.wells_by_name()[dest],
            mix_after=(json_params["mastermix_mix_cycles"], mixing_volume),
            blow_out=True,
            blowout_location="destination well",
            new_tip="always",
        )

    ########## THERMOCYCLING CONDITIONS ##########
    well_total_volumes = []
    for vol_mastermix, vol_water in zip(mastermix_volume, water_volume):
        well_total_volumes.append(vol_mastermix + vol_water)
    max_reaction_volume = max(well_total_volumes)

    thermocycler_mod.close_lid()
    thermocycler_mod.set_lid_temperature(temperature=json_params["lid_temp"])
    thermocycler_mod.set_block_temperature(
        temperature=json_params["initial_denaturation_temp"],
        hold_time_minutes=json_params["initial_denaturation_time_min"],
    )

    thermocycling_profile = [
        {
            "temperature": json_params["denaturation_temp"],
            "hold_time_seconds": json_params["denaturation_time_sec"],
        },  # Denaturation
        {
            "temperature": json_params["annealing_temp"],
            "hold_time_seconds": json_params["annealing_time_sec"],
        },  # Annealing
        {
            "temperature": json_params["extension_temp"],
            "hold_time_seconds": json_params["extension_time_sec"],
        },
    ]  # Extension
    thermocycler_mod.execute_profile(
        steps=thermocycling_profile,
        repetitions=json_params["amplification_cycles"],
        block_max_volume=max_reaction_volume,
    )
    thermocycler_mod.set_block_temperature(
        temperature=json_params["final_extension_temp"],
        hold_time_minutes=json_params["final_extension_time_min"],
    )  # Final extension
    thermocycler_mod.set_block_temperature(temperature=json_params["hold_temp"])  # Hold

    protocol.comment("Protocol completed successfully.")
