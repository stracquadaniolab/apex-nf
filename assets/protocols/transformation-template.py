from opentrons import protocol_api
import json
import csv
import collections

metadata = {
    "apiLevel": "2.13",
    "protocolName": "E. coli heatshock transformation",
    "description": "OT-2 protocol for standard E. coli heatshock transformation.",
    "author": "Martyna Kasprzyk",
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


def read_csv_file(csv_file):

    csv_data = csv_file.splitlines()[1:]  # Discard the blank first line.
    csv_reader = csv.DictReader(csv_data)

    # if multi channel
    seen_numbers = {}
    result_rows = []

    for row in csv_reader:
        well = row["dna_well"]
        letter, number = well[0], well[1:]

        # Check if the number is already associated with a different letter
        if number in seen_numbers and seen_numbers[number] != letter:
            continue

        result_rows.append(row)
        seen_numbers[number] = letter

    cells_source_wells = []
    cells_volume = []
    dna_source_wells = []
    dna_volume = []
    soc_source_wells = []
    soc_volume = []
    transformation_well = []

    for row in result_rows:
        cells_source_wells.append(row["cells_well"])
        cells_volume.append(int(row["cells_volume"]))
        dna_source_wells.append(row["dna_well"])
        dna_volume.append(int(row["dna_volume"]))
        soc_source_wells.append(row["soc_well"])
        soc_volume.append(int(row["soc_volume"]))
        transformation_well.append(row["transformation_well"])

    csv_parameters = collections.namedtuple(
        "csv_parameters",
        [
            "cells_source_wells",
            "cells_volume",
            "dna_source_wells",
            "dna_volume",
            "soc_source_wells",
            "soc_volume",
            "transformation_well",
        ],
    )

    return csv_parameters(
        cells_source_wells,
        cells_volume,
        dna_source_wells,
        dna_volume,
        soc_source_wells,
        soc_volume,
        transformation_well,
    )


def get_parameters(json_file: str) -> dict:
    """
    This function parses the json file with the parameters for the experiment and returns them as a dictionary.
    """
    parameters = json.loads(json_file)  # load and parse the parameter json file
    return parameters


def run(protocol: protocol_api.ProtocolContext):
    """
    Main function for running the protocol.
    """

    params = get_parameters(INPUT_JSON_FILE)  # load the parameters from the json file
    csv_params = read_csv_file(INPUT_CSV_FILE)

    # loading hardware and labware
    source_plate = protocol.load_labware(
        params["dna_plate_name"], params["dna_plate_slot"]
    )  # plate containing dna to be transformed
    thermocycler_mod = protocol.load_module(
        "thermocycler"
    )  # thermocycler module, takes location 7,8,10,11
    transformation_plate = thermocycler_mod.load_labware(
        params["transformation_plate_name"]
    )  # plate where transformations take place, loaded onto thermocycler module

    pipette_1_tipracks = [
        protocol.load_labware(load_name=params["pipette_1_tiprack_name"], location=i)
        for i in params["pipette_1_tiprack_slots"]
    ]
    pipette_1 = protocol.load_instrument(
        instrument_name=params["pipette_1_name"],
        mount=params["pipette_1_mount"],
        tip_racks=pipette_1_tipracks,
    )  # p20 pipette

    pipette_2_tipracks = [
        protocol.load_labware(load_name=params["pipette_2_tiprack_name"], location=i)
        for i in params["pipette_2_tiprack_slots"]
    ]
    pipette_2 = protocol.load_instrument(
        instrument_name=params["pipette_2_name"],
        mount=params["pipette_2_mount"],
        tip_racks=pipette_2_tipracks,
    )  # p300 pipette

    # loading liquid handling settings
    pipette_2.flow_rate.aspirate = 10  # aspirate speed of the pipette
    pipette_2.flow_rate.dispense = 10  # dispense speed of the pipette

    ########## HEAT-SHOCK TRANSFORMATION ##########
    protocol.comment("Starting heat-shock transformation.")
    protocol.set_rail_lights(True)

    # step 1: Preheat the module and open lid.
    thermocycler_mod.set_block_temperature(temperature=params["init_temp"])
    thermocycler_mod.open_lid()

    # step 2: Transferring competent cells into the transformation plate.
    protocol.pause(
        "Put plate on the thermocycler module and click 'resume'."
    )  # wait for operator to put the plate

    pipette_2.distribute(
        volume=csv_params.cells_volume,  # volume of competent cells to be transferred
        source=[
            source_plate.wells_by_name()[well] for well in csv_params.cells_source_wells
        ],  # transfer from the specified well in the resevoir containing competent cells
        dest=[
            transformation_plate.wells_by_name()[well]
            for well in csv_params.transformation_well
        ],  # transfer to transformation plate in the thermocycler
        mix_before=(1, 50),
    )  # resuspend the competent cells once before transfering into the transformation plate with the total volume to be trasfered, volume not specified sets the default to the max volume of pipette

    # step 3: Transfer DNA into wells of the transformation plate.
    pipette_1.well_bottom_clearance.aspirate = (
        0.5  # aspiration height of the pipette (when volume of DNA is low)
    )

    for i in zip(
        csv_params.dna_source_wells,
        csv_params.transformation_well,
        csv_params.dna_volume,
        csv_params.cells_volume,
    ):
        pipette_1.pick_up_tip()
        pipette_1.well_bottom_clearance.aspirate = 0.5
        pipette_1.aspirate(volume=i[2], location=source_plate.wells_by_name()[i[0]])
        pipette_1.well_bottom_clearance.aspirate = 1
        pipette_1.dispense(
            volume=i[2], location=transformation_plate.wells_by_name()[i[1]]
        )
        mixing_volume = (i[2] + i[3]) / 2
        pipette_1.aspirate(
            volume=mixing_volume, location=transformation_plate.wells_by_name()[i[1]]
        )
        pipette_1.dispense(
            volume=mixing_volume, location=transformation_plate.wells_by_name()[i[1]]
        )
        pipette_1.aspirate(
            volume=mixing_volume, location=transformation_plate.wells_by_name()[i[1]]
        )
        pipette_1.dispense(
            volume=mixing_volume, location=transformation_plate.wells_by_name()[i[1]]
        )
        pipette_1.blow_out(location=transformation_plate.wells_by_name()[i[1]])
        pipette_1.move_to(transformation_plate.wells_by_name()[i[1]].bottom())
        pipette_1.drop_tip()

    # step 4: Close the thermocycler lid and cool the thermocycler down for specified temperature and time, deafult: 4 degrees celcius and 20 minutes
    thermocycler_mod.close_lid()
    thermocycler_mod.set_block_temperature(
        temperature=params["init_temp"], hold_time_minutes=params["init_time"]
    )

    # step 5: Perform heat-shock transformation for specified temperature and time, deafult: 42 degrees celcius and 1 minute
    protocol.comment("Starting heat-shock transformation.")
    thermocycler_mod.set_block_temperature(
        temperature=params["heat_temp"], hold_time_seconds=params["heat_time"]
    )

    # step 6: Cool down thermocycler for specified temperature and time, default: 4 degrees celcius and 2 minutes.
    protocol.comment("Cool down thermocycler to 4C post heatshock")
    thermocycler_mod.set_block_temperature(
        temperature=params["cool_temp"], hold_time_minutes=params["cool_time"]
    )

    pipette_2.flow_rate.aspirate = 15  # aspirate speed of the pipette
    pipette_2.flow_rate.dispense = 15  # dispense speed of the pipette

    # step 7: Open the thermocycler lid and transfer SOC media to transformed cells.
    thermocycler_mod.open_lid()

    for i in zip(
        csv_params.soc_source_wells,
        csv_params.transformation_well,
        csv_params.soc_volume,
        csv_params.dna_volume,
        csv_params.cells_volume,
    ):
        pipette_2.pick_up_tip()
        pipette_2.aspirate(volume=i[2], location=source_plate.wells_by_name()[i[0]])
        pipette_2.dispense(
            volume=i[2], location=transformation_plate.wells_by_name()[i[1]]
        )
        mixing_volume = (i[2] + i[3] + i[4]) / 2
        for _ in range(3):
            pipette_2.aspirate(
                volume=mixing_volume,
                location=transformation_plate.wells_by_name()[i[1]],
            )
            pipette_2.dispense(
                volume=mixing_volume,
                location=transformation_plate.wells_by_name()[i[1]],
            )

        pipette_2.blow_out(location=transformation_plate.wells_by_name()[i[1]])
        pipette_2.move_to(transformation_plate.wells_by_name()[i[1]].bottom())
        pipette_2.drop_tip()

    # step 8: Close the thermocycler lid and heat up both thermocycler block and lid for specified temperature and time, default: 37 celcius degrees and 60 minutes
    thermocycler_mod.close_lid()
    thermocycler_mod.set_lid_temperature(temperature=params["inc_temp"])
    thermocycler_mod.set_block_temperature(
        temperature=params["inc_temp"], hold_time_minutes=params["inc_time"]
    )
    protocol.comment("Starting incubation.")
    protocol.set_rail_lights(False)

    # step 9: Finish incubation and deactivate the thermocycler module.
    protocol.comment("Incubation finished.")
    thermocycler_mod.deactivate_lid()
    thermocycler_mod.deactivate()

    protocol.comment("Run complete!")
