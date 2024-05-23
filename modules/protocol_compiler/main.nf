process MAKE_PROTOCOL_1 {

    publishDir "${params.resultsDir}", pattern: "protocol-1.py", mode: 'copy'

    input:
        tuple path(config), path(csv)
        path(template_dir)

    output:
        path 'protocol-1.py'

    script:
    """
        protocol-compiler.py -d ${template_dir} -o protocol-1.py \
            protocol-1-template.py ${config} ${csv}
    """

    stub: 
    """
        touch protocol-1.py
    """

}

process MAKE_PROTOCOL_2 {

    publishDir "${params.resultsDir}", pattern: "protocol-2.py", mode: 'copy'

    input:
        tuple path(config), path(csv)
        path(template_dir)

    output:
        path 'protocol-2.py'

    script:
    """
        protocol-compiler.py -d ${template_dir} -o protocol-2.py \
            protocol-2-template.py ${config} ${csv}
    """

    stub: 
    """
        touch protocol-2.py
    """

}

process MAKE_PROTOCOL_3 {

    publishDir "${params.resultsDir}", pattern: "protocol-3.py", mode: 'copy'

    input:
        tuple path(config), path(csv)
        path(template_dir)

    output:
        path 'protocol-3.py'

    script:
    """
        protocol-compiler.py -d ${template_dir} -o protocol-3.py \
            protocol-3-template.py ${config} ${csv}
    """

    stub: 
    """
        touch protocol-3.py
    """

}

process SIMULATE_PROTOCOL {

    publishDir "${params.resultsDir}", mode: 'copy'

    input:
        path(protocol)

    output:
        path 'protocol_simulation.txt'

    script:
    """
        opentrons_simulate ${protocol} > protocol_simulation.txt
    """

    stub: 
    """
        touch protocol_simulation.txt
    """

}
