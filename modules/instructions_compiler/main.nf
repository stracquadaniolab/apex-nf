process CREATE_LABWARE_CSV {

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

process MAKE_INSTRUCTIONS_1 {

    publishDir "${params.resultsDir}", pattern: "protocol-1-instructions.pdf", mode: 'copy'

    input:
        path(markdown_file)
        path(config)
        path(plots)

    output:
    path "protocol-1-instructions.pdf"

    script:
    """
    R -e "rmarkdown::render('${markdown_file}', output_file = 'protocol-1-instructions.pdf', params = list(json_path = '${config}', labware_images_dir = '${plots}'))"
    """

    stub: 
    """
        touch protocol-1-instructions.pdf
    """

}

process MAKE_INSTRUCTIONS_2 {

    publishDir "${params.resultsDir}", pattern: "protocol-2-instructions.pdf", mode: 'copy'

    input:
        path(markdown_file)
        path(config)
        path(plots)

    output:
    path "protocol-2-instructions.pdf"

    script:
    """
    R -e "rmarkdown::render('${markdown_file}', output_file = 'protocol-2-instructions.pdf', params = list(json_path = '${config}', labware_images_dir = '${plots}'))"
    """

    stub: 
    """
        touch protocol-2-instructions.pdf
    """

}

process MAKE_INSTRUCTIONS_3 {

    publishDir "${params.resultsDir}", pattern: "protocol-3-instructions.pdf", mode: 'copy'

    input:
        path(markdown_file)
        path(config)
        path(plots)

    output:
    path "protocol-3-instructions.pdf"

    script:
    """
    R -e "rmarkdown::render('${markdown_file}', output_file = 'protocol-3-instructions.pdf', params = list(json_path = '${config}', labware_images_dir = '${plots}'))"
    """

    stub: 
    """
        touch protocol-3-instructions.pdf
    """
}

process MAKE_INSTRUCTIONS_4 {

    publishDir "${params.resultsDir}", pattern: "protocol-4-instructions.pdf", mode: 'copy'

    input:
        path(markdown_file)
        path(config)
        path(plots)

    output:
    path "protocol-4-instructions.pdf"

    script:
    """
    R -e "rmarkdown::render('${markdown_file}', output_file = 'protocol-4-instructions.pdf', params = list(json_path = '${config}', labware_images_dir = '${plots}'))"
    """

    stub: 
    """
        touch protocol-4-instructions.pdf
    """
}