include { Hello } from './modules/hello'

workflow {
    channel.fromPath("${params.inputFile}") | Hello
}
