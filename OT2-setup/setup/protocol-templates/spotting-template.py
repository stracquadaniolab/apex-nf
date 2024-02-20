from opentrons import protocol_api
import math
import csv
import json
import collections


metadata = {
    'apiLevel': '2.15',
    'protocolName': 'agar-plate-spotting',
    'description': 'Protocol for agar plate spotting.',
    'author': 'Martyna Kasprzyk'
}


def get_parameters(json_file: str) -> dict:
    """
    This function parses the json file with the parameters for the experiment and returns them as a dictionary.
    """
    parameters = json.loads(json_file) # load and parse the paraemter json file
    return parameters

def read_csv_file(csv_file):

    csv_data = csv_file.splitlines()[1:] # Discard the blank first line.
    csv_reader = csv.DictReader(csv_data)
    

    # if multi channel
    seen_numbers = {}
    result_rows = []
        
    for row in csv_reader:
            well = row['source_well']
            letter, number = well[0], well[1:]

            # Check if the number is already associated with a different letter
            if number in seen_numbers and seen_numbers[number] != letter:
                continue

            result_rows.append(row)
            seen_numbers[number] = letter

    plate_locations = []
    source_wells = []
    destination_wells = []
    spotting_volume = []
    agar_plate_weight = []

    for row in result_rows:

        if row['plate_location'] not in plate_locations:
             plate_locations.append(int(row['plate_location']))
        
        source_wells.append(row['source_well'])
        destination_wells.append(row['destination_well'])
        spotting_volume.append(int(row['spotting_volume']))
        agar_plate_weight.append(float(row['plate_weight']))

    # print(f"{plate_locations},{source_wells},{destination_wells},{spotting_volume}")
    csv_parameters = collections.namedtuple("csv_parameters", ["plate_locations", "source_wells", "destination_wells", "spotting_volume", "agar_plate_weight"])

    return csv_parameters(plate_locations, source_wells, destination_wells, spotting_volume, agar_plate_weight)

def agar_height(agar_plate_weight, just_plate, agar_density,spotting_height):
    bottom_area = math.pi*(83.5/2)**2
    agar_weight = agar_plate_weight - float(just_plate)
    agar_height = agar_weight/(bottom_area*agar_density)
    spotting_height = agar_height + spotting_height
    print(agar_weight)
    print(spotting_height)

    return spotting_height

# run protocol
def run(protocol: protocol_api.ProtocolContext):
    """
    Main function for running the protocol.
    """
    
    params = get_parameters(parameters_json) # load the parameters from the json file
    csv_params = read_csv_file(csv_file)

    # loading hardware and labware
    pipette_tipracks = [protocol.load_labware(load_name=params["pipette_tiprack_name"], location=i) for i in params["pipette_tiprack_slots"]]
    pipette = protocol.load_instrument(instrument_name=params["pipette_name"], mount=params["pipette_mount"], tip_racks=pipette_tipracks) # p20 pipette
    
    # source plate located in the thermocycler
    thermocycler_mod = protocol.load_module("thermocycler")  # thermocycler module, takes location 7,8,10,11
    transformation_plate = thermocycler_mod.load_labware(params["transformation_plate_name"]) # plate where transformations take place, loaded onto  thermocycler module

    # Extract the plate locations into a list
    agar_plates = [protocol.load_labware(load_name=params["agar_plate_name"],
                                         location=slot,
                                         label=f"Agar Plate {str(i+1)}") 
                                         for i, slot in enumerate(csv_params.plate_locations)]

    # protocol.comment(f"{agar_plates}")
    thermocycler_mod.open_lid()
    ######### SPOTTING ##########
    for plate, source, destination, volume, weight in zip(agar_plates, csv_params.source_wells, csv_params.destination_wells, csv_params.spotting_volume, csv_params.agar_plate_weight):
        pipette.well_bottom_clearance.dispense = 1
        pipette.pick_up_tip()
        pipette.mix(repetitions=3, volume=5, location=transformation_plate[source], rate=2)
        pipette.aspirate(volume=volume + params["dead_volume"], location=transformation_plate[source], rate=2)
        pipette.well_bottom_clearance.dispense = agar_height(weight, params["plate_weight"], params["agar_density"], params["spotting_height"])
        pipette.dispense(volume=volume, location=plate[destination], rate=4)
        protocol.delay(seconds=5)
        pipette.drop_tip()