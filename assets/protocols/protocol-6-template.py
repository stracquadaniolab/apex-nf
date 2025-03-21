from opentrons import protocol_api
import csv
import json
from collections import namedtuple, defaultdict
from typing import Tuple, List, Dict, NamedTuple, Any, Optional

metadata = {
    "apiLevel": "2.16",
    "protocolName": "Protocol 6: SDS PAGE Sample Preparation",
    "description": "OT-2 protocol for SDS PAGE sample preparation.",
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

    pipette_culture = select_pipette(data.culture_volume, available_pipettes)
    pipette_lysis = select_pipette(data.lysis_volume, available_pipettes)
    pipette_sds = select_pipette(data.sds_volume, available_pipettes)

    sds_distribution_map = defaultdict(list)
    source_well_volumes = {}
    for src, vol in zip(data.sds_source_well, data.sds_volume):
        if src not in source_well_volumes:
            source_well_volumes[src] = []
        source_well_volumes[src].append(vol)
    pipette_sds = select_pipette(
        data.sds_volume,
        available_pipettes,
        is_distribution=True,
        source_to_volumes_map=source_well_volumes,
    )

    loaded_plates = {}
    culture_plate = protocol.load_labware(
        load_name=json_params["culture_plate_name"],
        location=json_params["culture_plate_slot"],
    )

    reagent_plate = protocol.load_labware(
        load_name=json_params["reagent_plate_name"],
        location=json_params["reagent_plate_slot"],
    )

    lysis_plate = protocol.load_labware(
        load_name=json_params["lysate_plate_name"],
        location=json_params["lysate_plate_slot"],
    )

    thermocycler_mod = protocol.load_module("thermocycler")
    thermocycler_mod.open_lid()
    destination_plate = thermocycler_mod.load_labware(json_params["destination_plate_name"])

    default_aspirate_rate = pipette_culture.flow_rate.aspirate

    ########## TRANSFER CULTURES TO LYSIS PLATE ##########
    protocol.comment("Aliquoting the cultures.")
    culture_source, culture_volume, culture_destination = filter_compatible_data(
        pipette_culture,
        data.culture_source_well,
        data.culture_volume,
        data.destination_well,
    )

    for src, vol, dest in zip(culture_source, culture_volume, culture_destination):
        pipette_culture.transfer(
            volume=vol,
            source=culture_plate.wells_by_name()[src],
            dest=lysis_plate.wells_by_name()[dest],
            mix_before=(
                json_params["culture_mix_number"],
                json_params["culture_mix_volume"],
            ),
            blow_out=True,
            blowout_location="destination well",
            new_tip="always",
        )

    ########## PAUSE FOR CENTRIFUGATION ##########
    protocol.pause("Centrifuge the lysis plate, then click 'Resume'.")

    ########## DISCARD SUPERNATANT ##########
    protocol.comment("Discarding the supernatant.")
    # Adjust pipette settings for careful supernatant removal
    pipette_culture.well_bottom_clearance.aspirate = json_params[
        "pallet_well_bottom_clearance"
    ]
    pipette_culture.flow_rate.aspirate = json_params["supernatant_flow_rate_aspirate"]

    for src, vol, dest in zip(culture_source, culture_volume, culture_destination):
        pipette_culture.pick_up_tip()
        pipette_culture.aspirate(
            volume=vol,
            location=lysis_plate.wells_by_name()[dest],
        )
        pipette_culture.drop_tip()

    # Restore normal flow rate
    pipette_culture.flow_rate.aspirate = default_aspirate_rate

    ########## ADD LYSIS BUFFER ##########
    protocol.comment("Adding lysis buffer.")
    lysis_source, lysis_volume, lysis_destination = filter_compatible_data(
        pipette_lysis,
        data.lysis_source_well,
        data.lysis_volume,
        data.destination_well,
    )

    for src, vol, dest in zip(lysis_source, lysis_volume, lysis_destination):
        mixing_volume = vol / 2
        mixing_volume = (
            mixing_volume
            if mixing_volume <= pipette_lysis.max_volume / 2
            else pipette_lysis.max_volume
        )
        pipette_lysis.transfer(
            volume=vol,
            source=reagent_plate.wells_by_name()[src],
            dest=lysis_plate.wells_by_name()[dest],
            mix_after=(
                json_params["lysis_mix_number"],
                mixing_volume,
            ),
            blow_out=True,
            blowout_location="destination well",
            new_tip="always",
        )

    ########## LYSIS INCUBATION ##########
    protocol.comment(
        f"Incubating for {json_params['lysis_incubation_time_min']} minutes."
    )
    protocol.delay(minutes=json_params["lysis_incubation_time_min"])
    thermocycler_mod.open_lid()

    ########## PAUSE FOR CENTRIFUGATION ##########
    protocol.pause(
        "Centrifuge the lysis plate, place the SDS plate into the thermocycler, then click 'Resume'."
    )

    ########## DISTRIBUTE SDS SAMPLE BUFFER ##########
    protocol.comment("Distributing SDS buffer.")
    sds_source, sds_volume, sds_destination = filter_compatible_data(
        pipette_sds, data.sds_source_well, data.sds_volume, data.destination_well
    )

    for src, vol, dest in zip(sds_source, sds_volume, sds_destination):
        sds_distribution_map[src].append((vol, dest))

    pipette_sds.pick_up_tip()
    for src, volume_destination_pairs in sds_distribution_map.items():
        volumes = [pair[0] for pair in volume_destination_pairs]
        destinations = [pair[1] for pair in volume_destination_pairs]

        pipette_sds.distribute(
            volume=volumes,
            source=reagent_plate.wells_by_name()[src],
            dest=[destination_plate.wells_by_name()[well] for well in destinations],
            new_tip="never",
            blow_out=True,
            blowout_location="source well",
        )
    pipette_sds.drop_tip()

    ########## TRANSFER LYSATE TO SDS PLATE ##########
    protocol.comment("Transferring lysate.")
    lysis_source, lysis_volume, lysis_destination = filter_compatible_data(
        pipette_lysis,
        data.lysis_source_well,
        data.lysis_volume,
        data.destination_well,
    )
    for src, vol, dest in zip(lysis_source, lysis_volume, lysis_destination):
        pipette_lysis.transfer(
            volume=vol,
            source=lysis_plate.wells_by_name()[src],
            dest=destination_plate.wells_by_name()[dest],
            mix_after=(json_params["sds_mix_number"], vol),
            blow_out=True,
            blowout_location="destination well",
            new_tip="always",
        )

    ########## DENATURATION ##########
    protocol.comment("Starting dentauration.")
    well_total_volumes = []
    for vol_lysis, vol_sds in zip(lysis_volume, sds_volume):
        well_total_volumes.append(vol_lysis + vol_sds)
    max_reaction_volume = max(well_total_volumes)
    thermocycler_mod.close_lid()
    thermocycler_mod.set_lid_temperature(temperature=json_params["lid_temp"])
    thermocycler_mod.set_block_temperature(
        temperature=json_params["denaturation_temp"],
        hold_time_minutes=json_params["denaturation_time_min"],
        block_max_volume=max_reaction_volume,
    )
    thermocycler_mod.deactivate_lid()
    thermocycler_mod.deactivate_block()

    protocol.comment("Protocol completed successfully.")