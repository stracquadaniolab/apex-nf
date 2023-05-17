from opentrons import protocol_api

metadata = {
    'apiLevel': '2.13',
    'protocolName': 'enzyme screening platform',
    'description': '''End-to-end eznyme screening platform for argB.''',
    'author': 'Martyna Kasprzyk'
}

def run(protocol: protocol_api.ProtocolContext):
    protocol.comment('Starting test protocol')
    
    # loading equipment
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    p300 = protocol.load_instrument("p300_multi_gen2", "right", tip_racks=[tiprack])

    # distribute diluent
    p300.transfer(100, reservoir["A1"], plate.rows()[0])

    # save the destination row to a variable
    row = plate.rows()[0]

    # transfer solution to first well in column
    p300.transfer(100, reservoir["A2"], row[0], mix_after=(3, 50))

    # dilute the sample down the row
    p300.transfer(100, row[:11], row[1:], mix_after=(3, 50))
