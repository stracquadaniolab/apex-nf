nextflow.enable.dsl=2

process CreateProtocol {
    publishDir "${params.resultsDir}", mode: "copy", overwrite: true, pattern: "*.py"
    publishDir "${params.resultsDir}/labware", mode: "copy", overwrite: true, pattern: "*.csv"

    input:
        path(csvData)
        path(jsonParameters)
        path(protocolTemplate)

    output:
        path("protocol.py"), emit: protocol
        path("labware.csv"), emit: labware

    script:
    """
        create-protocol.py ${csvData} ${jsonParameters} ${protocolTemplate} protocol.py
        create-labware-csv.py ${csvData} ${jsonParameters} labware.csv

    """
}

process SimulateProtocol {
    publishDir "${params.resultsDir}", mode: "copy", overwrite: true, pattern: "*.py"

    input:
        path(opentronsProtocol)
    output:
        path("protocol-simulation.txt")

    script:
    """
    opentrons_simulate ${opentronsProtocol} > protocol-simulation.txt
    """
}

process VisualiseLabware {
    publishDir "${params.resultsDir}/labware", mode: "copy", overwrite: true

    input:
        path(csvLabware)
        path(opentronsLabware)

    output:
        path("plots"), emit: visual

    script:
    """
        visualise-labware.R ${csvLabware} ${opentronsLabware}
    """
}

process CreateInstructions {
    publishDir "${params.resultsDir}", mode: "copy", overwrite: true

    input:
        path(instructionsTemplate)
        path(jsonParameters)
        path(visualLabware)

    output:
        path("instructions.pdf")

    script:
    """
        ${instructionsTemplate} ${jsonParameters} ${visualLabware} instructions.pdf
    """
}

workflow {
    csv_file_channel = Channel.fromPath(params.csvFile)
    json_file_channel = Channel.fromPath(params.jsonFile)
    protocol_template_channel = Channel.fromPath(params.templateFile)
    labware_folder_channel = Channel.fromPath(params.labwareFolder)
    instructions_template_channel = Channel.fromPath(params.instructionsFile)

    CreateProtocol(csv_file_channel, json_file_channel, protocol_template_channel)
    // SimulateProtocol(CreateProtocol.out.protocol)
    // VisualiseLabware(CreateProtocol.out.labware, labware_folder_channel)
    // CreateInstructions(instructions_template_channel, json_file_channel, VisualiseLabware.out.visual)
}