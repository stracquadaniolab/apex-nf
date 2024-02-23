process MAKE_TRANSFORMATION_PROTOCOL {

    publishDir "${params.resultsDir}", pattern: "transformation_protocol.py", mode: 'copy'

    input:
        tuple path(config), path(csv)
        path(template_dir)

    output:
        path 'transformation_protocol.py'

    script:
    """
        protocol-compiler.py -d ${template_dir} -o transformation_protocol.py \
            transformation-template.py ${config} ${csv}
    """

    stub: 
    """
        touch transformation_protocol.py
    """

}

process MAKE_SPOTTING_PROTOCOL {

    publishDir "${params.resultsDir}", pattern: "spotting_protocol.py", mode: 'copy'

    input:
        tuple path(config), path(csv)
        path(template_dir)

    output:
        path 'spotting_protocol.py'

    script:
    """
        protocol-compiler.py -d ${template_dir} -o spotting_protocol.py \
            spotting-template.py ${config} ${csv}
    """

    stub: 
    """
        touch spotting_protocol.py
    """

}