process CREATE_LABWARE_CSV {
    publishDir "${params.resultsDir}", mode: "copy"

    input:
        tuple path(csv), path(config)

    output:
        path("labware.csv")

    script:
    """
        create-labware.py ${csv} ${config} labware.csv
    """
}

process VISUALISE_LABWARE {
    publishDir "${params.resultsDir}", mode: "copy"

    input:
        path(csv_labware)
        path(opentrons_dir)

    output:
        path("plots")

    script:
    """
        visualise-labware.R ${csv_labware} ${opentrons_dir}
    """
} 

process CREATE_INSTRUCTIONS {
    publishDir "${params.resultsDir}", mode: "copy"

    input:
        path(config)
        path(plots)

    output:
        path("instructions.pdf")

    script:
    """
        protocol-1.R ${config} ${plots} instructions.pdf
    """
}