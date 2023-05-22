from opentrons import protocol_api
import json
import collections

metadata = {
    "apiLevel": "2.13",
    "protocolName": "enzyme screening platform",
    "description": "End-to-end eznyme screening platform for argB.",
    "author": "Martyna Kasprzyk"
}

def get_parameters(json_file: str) -> dict:
    """
    This function parses the json file with the parameters for the experiment and returns them as a dictionary.
    """

    with open(json_file) as file:
        parameters = json.load(file) # load and parse the paraemter json file
    return parameters

def get_volumes(params):

    TX_VOLUME = params["dna_volume"] + params["cc_volume"]
    TX_HOLD_VOLUME = min(TX_VOLUME, 25)
    INCUBATION_VOLUME = params["dna_volume"] + params["cc_volume"] + params["soc_volume"]
    INCUBATION_HOLD_VOLUME = max(INCUBATION_VOLUME, 25)
    volumes = collections.namedtuple("volumes", ["TX_VOLUME", "TX_HOLD_VOLUME", "INCUBATION_VOLUME", "INCUBATION_HOLD_VOLUME"])
    return volumes(TX_VOLUME, TX_HOLD_VOLUME, INCUBATION_HOLD_VOLUME, INCUBATION_HOLD_VOLUME)

def agar_wells_generation(params: dict, agar_plates) -> list:
    """
    Returns the list of wells on the destination agar plates to be spotted.
    """
    remainder = params["transformations_n"] % params["agar_max_wells_n"] # number of remainder transformations after dividing by the max number of wells on the destination plate
    if remainder == 0: # when the plate(s) is/are full
        agar_wells_list = [plate.wells() for plate in agar_plates]
    else: # when the number of transformation is less than max number of wells on the destination plate
        agar_wells_list = [plate.wells() for plate in agar_plates]
        del agar_wells_list[-1][remainder:] # delete destination wells if empty
    return agar_wells_list

def run(protocol: protocol_api.ProtocolContext):
    """
    Main function for running the protocol.
    """

    # loading experiment parameters
    params = get_parameters("parameters.json") # loading dictionary with parameters from parsed json file
    volumes = get_volumes(params)
    
    # loading hardware and labware
    dna_plate = protocol.load_labware(params["dna_plate_loadname"], params["dna_plate_slot"]) # plate containing dna to be transformed
    reservoir = protocol.load_labware(params["reservoir_loadname"], params["reservoir_slot"]) # reservoir containing soc media and competent cells
    reservoir_soc = reservoir.wells()[:params["transformations_n"]]  # wells containing soc media in the reservoir [A1,B1,C1,...]
    reservoir_cc = reservoir.wells_by_name()[params["competent_cells_well"]] # well containing competent cells in the reservoir
    thermocycler_mod = protocol.load_module("thermocycler")  # thermocycler module, takes location 7,8,10,11
    transformation_plate = thermocycler_mod.load_labware(params["transformation_plate_loadname"]) # plate where transformations take place, loaded onto  thermocycler module
    thermocycler_mod.open_lid()

    p20_tiprack = protocol.load_labware(load_name=params["p20_tiprack_loadname"], location=params["p20_tiprack_slot"]) # p20 tiprack
    p20 = protocol.load_instrument(instrument_name=params["p20_name"], mount=params["p20_mount"], tip_racks=[p20_tiprack]) # p20 pipette
    p300_tiprack = protocol.load_labware(load_name=params["p300_tiprack_loadname"], location=params["p300_tiprack_slot"]) # p300 tiprack
    p300 = protocol.load_instrument(instrument_name=params["p300_name"], mount=params["p300_mount"], tip_racks=[p300_tiprack]) # p300 pipette
    
    # loading custom agar plates for spotting
    try: # if custom labware uploaded in the Opentrons App
        if params["agar_incubation"] == True:
            temp_mod = protocol.load_module('temperature module gen2', params["temp_mod_slot"])
            agar_plates = [temp_mod.load_labware(params["agar_plate_loadname"])]
        else:
            agar_plates = [protocol.load_labware(load_name=params["agar_plate_loadname"],
                                             location=slot,
                                             label=f"Agar Plate {str(i+1)}",
                                             namespace="custom_beta"
                                             ) for i, slot in enumerate(params["agar_slot"])] # list of agar plates consisting of: plate name, location
    except: # if custom labware not uploaded in the Opentrons App
        LABWARE_DEF = json.loads(params["agar_def_json"]) # custom labware agar plate
        agar_plates = [protocol.load_labware_from_definition(labware_def=LABWARE_DEF,
                                                             location=slot,
                                                             label=f"Agar Plate {str(i+1)}"
                                                            ) for i, slot in enumerate(params["agar_slot"])] # list of agar plates consisting of: plate name, location
    
    # load custom agar plates wells
    agar_wells = agar_wells_generation(params, agar_plates) # agar wells [A1, B1, C1, ...]
    protocol.comment(f"here: {agar_wells}")

    # loading liquid handling settings
    p20.flow_rate.aspirate = params["aspirate_rate"] # aspirate speed
    p20.flow_rate.dispense = params["dispense_rate"] # dispense speed
    

    ### HEAT-SHOCK TRANSFORMATION ###
    protocol.comment("Starting heat-shock transformation.")

    # step 1: Preheat the module and open lid.
    thermocycler_mod.set_block_temperature(temperature=params["init_temp"])
    thermocycler_mod.open_lid()

    # step 2: Transfering soc media into wells of the transfromation plate.
    protocol.pause("Put plate  on the thermocycler module and click 'resume'.") # wait for operator to put the plate
    protocol.comment(f"Transfering {params['cc_volume']} µL of competent cells into transformation plate. Final volume: {params['cc_volume']} µL.")
    p20.transfer(volume=params["cc_volume"], # volume of competent cells to be transfered
                 source=reservoir_cc, # transfer from the specified well in the resevoir containing competent cells
                 dest=transformation_plate.wells()[:params["transformations_n"]], # transfer to transformation plate in the thermocycler
                 mix_before=(1, params["cc_volume"]), # resuspend the competent cells once before transfering into the transformation plate with the total volume to be trasfered
                 new_tip="once") # use one tip for transfering all competent cells

    # step 3: Transfer DNA into wells of the transformation plate.
    protocol.comment(f"Transfering {params['dna_volume']} µL of DNA into {params['cc_volume']} µL of competent cells on the transfromation plate. Final volume: {volumes.TX_VOLUME} µL.")
    p20.transfer(volume=params["dna_volume"],  # volume of DNA to be transfered
                 source=dna_plate.wells()[:params["transformations_n"]],  # transfer from wells of the plate containing DNA
                 dest=transformation_plate.wells()[:params["transformations_n"]],  # transfer to transformation plate in the thermocycler
                 mix_after=(3, volumes.TX_VOLUME/2), # mix DNA with the competent cells 3 times with half the total volume
                 new_tip="always") # use a new tip every time new DNA is aliquoted
    
    # step 4: Close the thermocycler lid and cool the thermocycler down for specified temperature and time, deafult: 4 degrees celcius and 20 minutes
    thermocycler_mod.close_lid()
    thermocycler_mod.set_block_temperature(temperature=params["init_temp"], 
                                           hold_time_minutes=params["init_time"], 
                                           block_max_volume=volumes.TX_HOLD_VOLUME)
    
    # step 5: Perform heat-shock transformation for specified temperature and time, deafult: 42 degrees celcius and 1 minute
    protocol.comment("Starting heat-shock transformation.")
    thermocycler_mod.set_block_temperature(temperature=params["heat_temp"], 
                                           hold_time_minutes=params["heat_time"], 
                                           block_max_volume=volumes.TX_HOLD_VOLUME)
    
    # step 6: Cool down thermocycler for specified temperature and time, default: 4 degrees celcius and 2 minutes.
    protocol.comment("Cool down thermocycler to 4C post heatshock")
    thermocycler_mod.set_block_temperature(temperature=params["cool_temp"],
                                           hold_time_minutes=params["cool_time"],
                                           block_max_volume=volumes.TX_HOLD_VOLUME)

    # step 7: Open the thermocycler lid and transfer SOC media to transformed cells.
    thermocycler_mod.open_lid()
    protocol.comment(f"Transfering {params['soc_volume']} µL of SOC media into {volumes.TX_VOLUME} µL of transformed cells. Final volume: {volumes.INCUBATION_VOLUME} µL.")
    p300.transfer(volume=params["soc_volume"],  # volume of SOC media to be transfered
                  source=reservoir_soc, # transfer from the well in the resevoir containing SOC media
                  dest=transformation_plate.wells()[:params["transformations_n"]], # transfer to transformation plate in the thermocycler
                  mix_after=(2, volumes.INCUBATION_VOLUME/2), # mix SOC with the transformed cells 3 times with half the total volume
                  new_tip="always") # use a new tip every time SOC is aliquoted
    
    # step 8: Close the thermocycler lid and heat up both thermocycler block and lid for specified temperature and time, default: 37 celcius degrees and 60 minutes
    thermocycler_mod.close_lid()
    protocol.comment("Starting incubation.")
    thermocycler_mod.set_lid_temperature(temperature=params["inc_temp"])
    thermocycler_mod.set_block_temperature(temperature=params["inc_temp"], 
                                           hold_time_minutes=params["inc_time"], 
                                           block_max_volume = volumes.INCUBATION_HOLD_VOLUME)
    
    # step 9: Finish incubation and deactivate the thermocycler module.
    protocol.comment("Incubation finished.")
    thermocycler_mod.deactivate_lid()
    thermocycler_mod.deactivate()

    ### AGAR PLATE SPOTTING ###
    protocol.comment("Starting agar plate spotting.") # start the agar spotting protcol
    protocol.set_rail_lights(True) # turn on the lights

    #testing dispense height before starting the spotting
    p20.well_bottom_clearance.dispense = params["agar_dispense_height"] # adjusting dispense height for agar plate spotting
    if params["test_dispense_height"] == True:
        protocol.comment("Begin testing the dispense height at agar plate")
        p20.pick_up_tip()
        for plate in agar_plates:
            well_first = plate.well(0)
            p20.move_to(well_first.bottom(z=params["dispense_height"]))
            protocol.pause("If the position is accurate click resume.")
            well_last = plate.well(-1)
            p20.move_to(well_last.bottom(z=params["dispense_height"]))
            protocol.pause("If the position is accurate click resume.")
        p20.return_tip()
    else:
        pass

    # step 10: Open the thermocycler and spot the transfromed cells onto the agar plate(s).
    thermocycler_mod.open_lid()    
    p20.transfer(volume=params["spot_volume"], # spotting volume
                 source=transformation_plate.wells()[:params["transformations_n"]], # transfer from the wells in the transfromation plate
                 dest=agar_wells, # transfer to agar plates
                 mix_before=(3, 20), # resuspend the cells 3 times before transfering onto the agar plate with the max volume fo the pipette
                 new_tip="always") # use a new tip after each spotting
    
    protocol.comment("Agar plate spotting finished.") # finish the agar spotting protocol
    protocol.set_rail_lights(False) # turn off the lights
    
    # if the incubation in place chosen, adjust temperature module on to the specified temperature
    if params["agar_incubation"] == True:
        protocol.comment("Starting incubation.")
        temp_mod.set_temperature(celsius=params["agar_incubation_temp"])
    
    protocol.comment("Run complete!")