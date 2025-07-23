from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional

metadata = {
    "apiLevel": "2.16",
    "protocolName": "Protocol 4: Protein Expression Induction",
    "description": "OT-2 protocol for protein expression induction.",
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
    """Filters out sources, volumes, and destinations. Adjusts wells to start with "A" for 8-channel pipettes, unless source is "NA".
    Leaves data unmodified for single-channel pipettes."""
    seen_columns, filtered_sources, filtered_volumes, filtered_destinations = (
        set(),
        [],
        [],
        [],
    )
    is_multi_channel = "8-Channel" in str(pipette)

    for source, volume, destination in zip(sources, volumes, destinations):
        if (
            source == "NA"
            or (
                formatted_destination := (
                    "A" + destination[1:] if is_multi_channel else destination
                )
            )
            in seen_columns
        ):
            continue

        seen_columns.add(formatted_destination)
        formatted_source = (
            "A" + source[1:] if is_multi_channel and source != "NA" else source
        )
        filtered_sources.append(formatted_source)
        filtered_volumes.append(volume)
        filtered_destinations.append(formatted_destination)

    return filtered_sources, filtered_volumes, filtered_destinations

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

    loaded_plates = {}
    culture_plate = load_or_reuse_labware(
        protocol,
        {
            "name": json_params["culture_plate_name"],
            "slot": json_params["culture_plate_slot"],
        },
        loaded_plates,
    )
    media_plate = load_or_reuse_labware(
        protocol,
        {
            "name": json_params["media_plate_name"],
            "slot": json_params["media_plate_slot"],
        },
        loaded_plates,
    )

    inducer_plate = load_or_reuse_labware(
        protocol,
        {
            "name": json_params["inducer_plate_name"],
            "slot": json_params["inducer_plate_slot"],
        },
        loaded_plates,
    )
    destination_plate = load_or_reuse_labware(
        protocol,
        {
            "name": json_params["destination_plate_name"],
            "slot": json_params["destination_plate_slot"],
        },
        loaded_plates,
    )

    available_pipettes = setup_pipettes(protocol, json_params)
    pipette_culture = select_pipette(data.culture_volume, available_pipettes)
    pipette_inducer = select_pipette(data.inducer_volume, available_pipettes)

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

    ########## DISTRIBUTE MEDIA ##########
    pipette_media.flow_rate.aspirate = 277.4
    pipette_media.flow_rate.dispense = 277.4
    pipette_media.flow_rate.blow_out = 277.4
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

    ########## CULTURE TRANSFER ##########
    culture_well, culture_volume, culture_destination = filter_compatible_data(
        pipette_culture, data.culture_source_well, data.culture_volume, data.destination_well
    )
    pipette_culture.transfer(
        volume=culture_volume,
        source=[culture_plate.wells_by_name()[well] for well in culture_well],
        dest=[destination_plate.wells_by_name()[well] for well in culture_destination],
        mix_before=(
            json_params["culture_mix_number"],
            json_params["culture_mix_volume"],
        ),
        new_tip="always",
    )

    protocol.pause(
        "Incubate the culture plate with shaking until it reaches the desired growth phase and click 'resume'."
    )

    ########## INDUCER TRANSFER ##########
    pipette_inducer.flow_rate.aspirate = 22.6
    pipette_inducer.flow_rate.dispense = 22.6
    pipette_inducer.flow_rate.blow_out = 22.6
    inducer_well, inducer_volume, inducer_destination = filter_compatible_data(
        pipette_inducer, data.inducer_source_well, data.inducer_volume, data.destination_well
    )
    pipette_inducer.transfer(
        volume=inducer_volume,
        source=[inducer_plate.wells_by_name()[well] for well in inducer_well],
        dest=[destination_plate.wells_by_name()[well] for well in inducer_destination],
        new_tip="always",
    )
    protocol.set_rail_lights(False)
