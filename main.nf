include { MAKE_PROTOCOL_1; MAKE_PROTOCOL_2; MAKE_PROTOCOL_3;  MAKE_PROTOCOL_4} from './modules/protocol_compiler'
include { SIMULATE_PROTOCOL_1; SIMULATE_PROTOCOL_2; SIMULATE_PROTOCOL_3; SIMULATE_PROTOCOL_4; } from './modules/protocol_compiler'
include { CREATE_LABWARE_CSV as CREATE_LABWARE_CSV_1; CREATE_LABWARE_CSV as CREATE_LABWARE_CSV_2; CREATE_LABWARE_CSV as CREATE_LABWARE_CSV_3; CREATE_LABWARE_CSV as CREATE_LABWARE_CSV_4 } from './modules/instructions_compiler'
include { VISUALISE_LABWARE as VISUALISE_LABWARE_1; VISUALISE_LABWARE as VISUALISE_LABWARE_2; VISUALISE_LABWARE as VISUALISE_LABWARE_3; VISUALISE_LABWARE as VISUALISE_LABWARE_4 } from './modules/instructions_compiler'
include { MAKE_INSTRUCTIONS_1;  MAKE_INSTRUCTIONS_2; MAKE_INSTRUCTIONS_3; MAKE_INSTRUCTIONS_4} from './modules/instructions_compiler'

workflow PROTOCOL_1 {

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
    MAKE_INSTRUCTIONS_1( 
        file("$params.protocol_1_instructions"),
        file("$params.protocol_1_config"),
        VISUALISE_LABWARE_1.out
    )
}

workflow PROTOCOL_2 {

    // PROTOCOL 2 - SELECTION
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

    MAKE_INSTRUCTIONS_2( 
        file("$params.protocol_2_instructions"),
        file("$params.protocol_2_config"),
        VISUALISE_LABWARE_2.out
    )

}

workflow PROTOCOL_3 {

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

    MAKE_INSTRUCTIONS_3( 
        file("$params.protocol_3_instructions"),
        file("$params.protocol_3_config"),
        VISUALISE_LABWARE_3.out
    )

}

workflow PROTOCOL_4 {

    // PROTOCOL 4 - INDUCTION
    MAKE_PROTOCOL_4(
        tuple(file("$params.protocol_4_config"), file("$params.protocol_4_data")), 
        file("$params.protocol_template_dir")
    )
    SIMULATE_PROTOCOL_4(
        MAKE_PROTOCOL_4.out
    )
    CREATE_LABWARE_CSV_4(
        tuple(file("$params.protocol_4_data"), file("$params.protocol_4_config"))
    )
    VISUALISE_LABWARE_4(
        CREATE_LABWARE_CSV_4.out, 
        file("$params.opentrons_labware_dir")
    )

    MAKE_INSTRUCTIONS_4( 
        file("$params.protocol_4_instructions"),
        file("$params.protocol_4_config"),
        VISUALISE_LABWARE_4.out
    )

}

workflow {
    PROTOCOL_1()
    PROTOCOL_2()
    PROTOCOL_3()
    PROTOCOL_4()
}