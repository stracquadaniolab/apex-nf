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

process MAKE_PROTOCOL_4 {

    publishDir "${params.resultsDir}", pattern: "protocol-4.py", mode: 'copy'

    input:
        tuple path(config), path(csv)
        path(template_dir)

    output:
        path 'protocol-4.py'

    script:
    """
        protocol-compiler.py -d ${template_dir} -o protocol-4.py \
            protocol-4-template.py ${config} ${csv}
    """

    stub: 
    """
        touch protocol-4.py
    """
}

process MAKE_PROTOCOL_5 {

    publishDir "${params.resultsDir}", pattern: "protocol-5.py", mode: 'copy'

    input:
        tuple path(config), path(csv)
        path(template_dir)

    output:
        path 'protocol-5.py'

    script:
    """
        protocol-compiler.py -d ${template_dir} -o protocol-5.py \
            protocol-5-template.py ${config} ${csv}
    """

    stub: 
    """
        touch protocol-5.py
    """
}

process MAKE_PROTOCOL_6 {

    publishDir "${params.resultsDir}", pattern: "protocol-6.py", mode: 'copy'

    input:
        tuple path(config), path(csv)
        path(template_dir)

    output:
        path 'protocol-6.py'

    script:
    """
        protocol-compiler.py -d ${template_dir} -o protocol-6.py \
            protocol-6-template.py ${config} ${csv}
    """

    stub: 
    """
        touch protocol-6.py
    """
}

process MAKE_PROTOCOL_7 {

    publishDir "${params.resultsDir}", pattern: "protocol-7.py", mode: 'copy'

    input:
        tuple path(config), path(csv)
        path(template_dir)

    output:
        path 'protocol-7.py'

    script:
    """
        protocol-compiler.py -d ${template_dir} -o protocol-7.py \
            protocol-7-template.py ${config} ${csv}
    """

    stub: 
    """
        touch protocol-7.py
    """
}

process SIMULATE_PROTOCOL_1 {

    publishDir "${params.resultsDir}", pattern: "protocol-1-simulation.txt", mode: "copy"


    input:
        path(protocol)
        path(labware)

    output:
        path "protocol-1-simulation.txt"

    script:
    """
        opentrons_simulate ${protocol} -L ${labware} > protocol-1-simulation.txt
    """

    stub: 
    """
        touch protocol-1-simulation.txt
    """
}

process SIMULATE_PROTOCOL_2 {

    publishDir "${params.resultsDir}", pattern: "protocol-2-simulation.txt", mode: "copy"


    input:
        path(protocol)
        path(labware)

    output:
        path "protocol-2-simulation.txt"

    script:
    """
        opentrons_simulate ${protocol} -L ${labware} > protocol-2-simulation.txt
    """

    stub: 
    """
        touch protocol-2-simulation.txt
    """
}

process SIMULATE_PROTOCOL_3 {

    publishDir "${params.resultsDir}", pattern: "protocol-3-simulation.txt", mode: "copy"


    input:
        path(protocol)
        path(labware)

    output:
        path "protocol-3-simulation.txt"

    script:
    """
        opentrons_simulate ${protocol} -L ${labware} > protocol-3-simulation.txt
    """

    stub: 
    """
        touch protocol-3-simulation.txt
    """
}

process SIMULATE_PROTOCOL_4 {

    publishDir "${params.resultsDir}", pattern: "protocol-4-simulation.txt", mode: "copy"

    input:
        path(protocol)
        path(labware)

    output:
        path "protocol-4-simulation.txt"

    script:
    """
        opentrons_simulate ${protocol} -L ${labware} > protocol-4-simulation.txt
    """

    stub: 
    """
        touch protocol-4-simulation.txt
    """
}

process SIMULATE_PROTOCOL_5 {

    publishDir "${params.resultsDir}", pattern: "protocol-5-simulation.txt", mode: "copy"

    input:
        path(protocol)
        path(labware)

    output:
        path "protocol-5-simulation.txt"

    script:
    """
        opentrons_simulate ${protocol} -L ${labware} > protocol-5-simulation.txt
    """

    stub: 
    """
        touch protocol-5-simulation.txt
    """
}

process SIMULATE_PROTOCOL_6 {

    publishDir "${params.resultsDir}", pattern: "protocol-6-simulation.txt", mode: "copy"

    input:
        path(protocol)
        path(labware)

    output:
        path "protocol-6-simulation.txt"

    script:
    """
        opentrons_simulate ${protocol} -L ${labware} > protocol-6-simulation.txt
    """

    stub: 
    """
        touch protocol-6-simulation.txt
    """
}


process SIMULATE_PROTOCOL_7 {

    publishDir "${params.resultsDir}", pattern: "protocol-7-simulation.txt", mode: "copy"

    input:
        path(protocol)
        path(labware)

    output:
        path "protocol-7-simulation.txt"

    script:
    """
        opentrons_simulate ${protocol} -L ${labware} > protocol-7-simulation.txt
    """

    stub: 
    """
        touch protocol-7-simulation.txt
    """
}