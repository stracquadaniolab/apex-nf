include { MAKE_PROTOCOL_1; MAKE_PROTOCOL_2; MAKE_PROTOCOL_3} from './modules/protocol_compiler'
include { SIMULATE_PROTOCOL as SIMULATE_PROTOCOL_1; SIMULATE_PROTOCOL as SIMULATE_PROTOCOL_2; SIMULATE_PROTOCOL as SIMULATE_PROTOCOL_3} from './modules/protocol_compiler'
include { CREATE_LABWARE_CSV as CREATE_LABWARE_CSV_1; VISUALISE_LABWARE as VISUALISE_LABWARE_1; CREATE_INSTRUCTIONS as CREATE_INSTRUCTIONS_1 } from './modules/instructions_compiler'
include { CREATE_LABWARE_CSV as CREATE_LABWARE_CSV_2; VISUALISE_LABWARE as VISUALISE_LABWARE_2; CREATE_INSTRUCTIONS as CREATE_INSTRUCTIONS_2 } from './modules/instructions_compiler'
include { CREATE_LABWARE_CSV as CREATE_LABWARE_CSV_3; VISUALISE_LABWARE as VISUALISE_LABWARE_3; CREATE_INSTRUCTIONS as CREATE_INSTRUCTIONS_3 } from './modules/instructions_compiler'


workflow {

<<<<<<< HEAD
    // PROTOCOL 1 - TRANSFORMATION
    MAKE_PROTOCOL_1(
        tuple(file("$params.protocol_1_config"), file("$params.protocol_1_data")), 
        file("$params.protocol_template_dir")
    )
    SIMULATE_PROTOCOL_1(
        MAKE_PROTOCOL_1.out
    )
    CREATE_LABWARE_CSV_1(
        tuple(file("$params.protocol_1_data"), file("$params.protocol_1_config"))
    )
    VISUALISE_LABWARE_1(
        CREATE_LABWARE_CSV_1.out, 
        file("$params.opentrons_labware_dir")
    )
    CREATE_INSTRUCTIONS_1(
        file("$params.protocol_1_config"),
        VISUALISE_LABWARE_1.out
    )

    // PROTOCOL 2 - SPOTTING
    MAKE_PROTOCOL_2(
        tuple(file("$params.protocol_2_config"), file("$params.protocol_2_data")), 
        file("$params.protocol_template_dir")
    )
    SIMULATE_PROTOCOL_2(
        MAKE_PROTOCOL_2.out
    )
    CREATE_LABWARE_CSV_2(
        tuple(file("$params.protocol_2_data"), file("$params.protocol_2_config"))
    )
    VISUALISE_LABWARE_2(
        CREATE_LABWARE_CSV_2.out, 
        file("$params.opentrons_labware_dir")
    )
    CREATE_INSTRUCTIONS_2(
        file("$params.protocol_2_config"),
        VISUALISE_LABWARE_2.out
    )

    // PROTOCOL 3 - SAMPLING
    MAKE_PROTOCOL_3(
        tuple(file("$params.protocol_3_config"), file("$params.protocol_3_data")), 
        file("$params.protocol_template_dir")
    )
    SIMULATE_PROTOCOL_3(
        MAKE_PROTOCOL_3.out
    )
    CREATE_LABWARE_CSV_3(
        tuple(file("$params.protocol_3_data"), file("$params.protocol_3_config"))
    )
    VISUALISE_LABWARE_3(
        CREATE_LABWARE_CSV_3.out, 
        file("$params.opentrons_labware_dir")
    )
    CREATE_INSTRUCTIONS_3(
        file("$params.protocol_3_config"),
        VISUALISE_LABWARE_3.out
    )

=======
    CreateProtocol(csv_file_channel, json_file_channel, protocol_template_channel)
    // SimulateProtocol(CreateProtocol.out.protocol)
    // VisualiseLabware(CreateProtocol.out.labware, labware_folder_channel)
    // CreateInstructions(instructions_template_channel, json_file_channel, VisualiseLabware.out.visual)
>>>>>>> refs/remotes/origin/main
}