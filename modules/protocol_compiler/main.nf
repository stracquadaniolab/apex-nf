process MAKE_TRANSFORMATION_PROTOCOL {

    publishDir "${params.resultsDir}", pattern: "results.txt", mode: 'copy'

    input:
        path data

    output:
        path 'results.txt'

    """
        cat ${data} > results.txt
    """

}

process MAKE_SPOTTING_PROTOCOL {

    publishDir "${params.resultsDir}", pattern: "results.txt", mode: 'copy'

    input:
        path data

    output:
        path 'results.txt'

    """
        cat ${data} > results.txt
    """

}