include { MAKE_TRANSFORMATION_PROTOCOL; MAKE_SPOTTING_PROTOCOL } from './modules/protocol_compiler'

workflow {

    MAKE_TRANSFORMATION_PROTOCOL(
        tuple(file("$params.transformation_config"), file("$params.transformation_data")), 
        file("$params.protocol_template_dir")
    )

    MAKE_SPOTTING_PROTOCOL(
        tuple(file("$params.spotting_config"), file("$params.spotting_data")), 
        file("$params.protocol_template_dir")
    )
    
}
