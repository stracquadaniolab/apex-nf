from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional

metadata = {
    "apiLevel": "2.16",
    "protocolName": "Protocol 7: OD600 Reading Sample Preparation",
    "description": "OT-2 protocol for OD600 reading sample preparation.",
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

# protocol run function
def run(protocol: protocol_api.ProtocolContext):
    params = load_json_data(INPUT_JSON_FILE)
    data = load_csv_data(INPUT_CSV_FILE)

    available_pipettes = setup_pipettes(protocol, params)
    pipette_culture = select_pipette(data.culture_volume, available_pipettes)
    diluent_plate = protocol.load_labware(
        load_name=params["diluent_plate_name"], location=params["diluent_plate_slot"]
    )
    culture_plate = protocol.load_labware(
        load_name=params["culture_plate_name"], location=params["culture_plate_slot"]
    )
    reading_plate = protocol.load_labware(
        load_name=params["reading_plate_name"], location=params["reading_plate_slot"]
    )

    diluent_distribution_map = defaultdict(list)

    source_well_volumes = {}
    for src, vol in zip(data.diluent_source_well, data.diluent_volume):
        if src not in source_well_volumes:
            source_well_volumes[src] = []
        source_well_volumes[src].append(vol)

    pipette_diluent = select_pipette(
        data.diluent_volume,
        available_pipettes,
        is_distribution=True,
        source_to_volumes_map=source_well_volumes,
    )

    ##### PROTOCOL STEPS #####

    ########## DISTRIBUTE DILUENT ##########
    protocol.comment("Diluent distribution.")
    diluent_source, diluent_volume, diluent_destination = filter_compatible_data(
        pipette_diluent,
        data.diluent_source_well,
        data.diluent_volume,
        data.destination_well,
    )
    for src, vol, dest in zip(diluent_source, diluent_volume, diluent_destination):
        diluent_distribution_map[src].append((vol, dest))

    pipette_diluent.pick_up_tip()
    for src, volume_destination_pairs in diluent_distribution_map.items():
        volumes = [pair[0] for pair in volume_destination_pairs]
        destinations = [pair[1] for pair in volume_destination_pairs]

        pipette_diluent.distribute(
            volume=volumes,
            source=diluent_plate.wells_by_name()[src],
            dest=[reading_plate.wells_by_name()[well] for well in destinations],
            new_tip="never",
            blow_out=True,
            blowout_location="source well",
        )
    pipette_diluent.drop_tip()

    ########## TRANSFER CULTURES ##########
    protocol.comment("Culture transfer.")
    culture_source, culture_volume, culture_destination = filter_compatible_data(
        pipette_culture,
        data.culture_source_well,
        data.culture_volume,
        data.destination_well,
    )
    diluent_source, diluent_volume, diluent_destination = filter_compatible_data(
        pipette_culture,
        data.diluent_source_well,
        data.diluent_volume,
        data.destination_well,
    )

    for src, vol_diluent, vol_culture, dest in zip(
        culture_source, diluent_volume, culture_volume, culture_destination
    ):
        mixing_volume = (vol_diluent + vol_culture) / 2
        mixing_volume = (
            mixing_volume
            if mixing_volume <= pipette_culture.max_volume / 2
            else pipette_culture.max_volume
        )

        pipette_culture.transfer(
            volume=int(vol_culture),
            source=culture_plate.wells_by_name()[src],
            dest=reading_plate.wells_by_name()[dest],
            mix_before=(params["culture_mix_number"], params["culture_mix_volume"]),
            mix_after=(2, mixing_volume),
            blow_out=True,
            blowout_location="destination well",
            new_tip="always",
        )
