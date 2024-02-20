#!/bin/bash

# Function to display usage information
usage() {
    echo "Usage: $0 experiment=experiment1,experiment2,... [csv_file=csv1,csv2,...] [json_file=json1,json2,...]"
    exit 1
}

# Check if the correct number of arguments is provided
if [ "$#" -lt 1 ]; then
    usage
fi

# Set default values
csv_files=""
json_files=""

# Parse command-line arguments
for arg in "$@"; do
    case $arg in
        experiment=*)
            experiment_types="${arg#*=}"
            ;;
        csv_file=*)
            csv_files="${arg#*=}"
            ;;
        json_file=*)
            json_files="${arg#*=}"
            ;;
        *)
            echo "Error: Invalid argument: $arg"
            usage
            ;;
    esac
done

# Function to check if a file exists
check_file_exists() {
    if [ ! -f "$1" ]; then
        echo "Error: $1 file not found."
        exit 1
    fi
}

# Function to extract variable from JSON
extract_variable_from_json() {
    local json_file="$1"
    local variable_name="$2"
    local variable_line=$(grep "$variable_name" "$json_file")

    # Extract the value part
    local variable_value=$(echo "$variable_line" | cut -d '"' -f 4)
    echo "$variable_value"
}

# Function to process each experiment type
process_experiment_type() {
    local experiment_type="$1"
    local input_csv="$2"
    local input_json="$3"

    local template_py=""
    
    case "$experiment_type" in
        transformation)
            template_py="./setup/protocol-templates/transformation-template.py"
            ;;
        spotting)
            template_py="./setup/protocol-templates/spotting-template.py"
            ;;
        *)
            echo "Error: Unsupported experiment type: $experiment_type"
            exit 1
            ;;
    esac

    # Check if the template Python file exists
    check_file_exists "$template_py"
    
    # If CSV file not specified, use default in "data" folder
    if [ -z "$input_csv" ]; then
        input_csv="data/${experiment_type}-data.csv"
    fi
    # If JSON file not specified, use default in "data" folder
    if [ -z "$input_json" ]; then
        input_json="data/${experiment_type}-parameters.json"
    fi
    
    # Check if the input CSV file exists
    check_file_exists "$input_csv"
    # Check if the input JSON file exists
    check_file_exists "$input_json"

    # Read contents of input CSV into a variable
    csv_content=$(<"$input_csv")

    # Define the content for protocol.py
    new_content="csv_file = \"\"\"\n$csv_content\n\"\"\"\n\n"
    # Read contents of input JSON into a variable and remove newlines
    json_content="parameters_json = \"\"\"$(<"$input_json" tr -d '\n' | tr -d '[:space:]'| tr -d '[:space:]')\"\"\"\n"

    # Extract the name from the template file
    template_name=$(basename "$template_py" | sed 's/.*\([a-zA-Z]\)-template\.py/\1/')
    # Generate the output file name in the "protocols" folder
    output_folder="results"
    output_file="${output_folder}/${experiment_type}-protocol.py"

    # Create the protocols folder if it doesn't exist
    mkdir -p "$output_folder"

    # If the file exists, append the new content at the top
    old_content=$(<"$template_py")
    echo -e "$new_content$json_content$old_content" > "$output_file"
    echo "Protocol for $experiment_type has been generated. Output file: $output_file"

    # Get the transformation_plate_name and dna_plate_name from the parameters JSON
    transformation_plate_name=$(extract_variable_from_json "$input_json" "transformation_plate_name")
    dna_plate_name=$(extract_variable_from_json "$input_json" "dna_plate_name")

    # Call the R scripts 
    Rscript ./setup/create-labware/visualise-labware.R ./data/labware.csv "${output_folder}"
    Rscript ./setup/create-labware/visualise-labware-2.R ./data/transformation-data.csv "${output_folder}"
    Rscript ./setup/instruction-templates/transformation-instruction.R "./data/transformation-parameters.json" "${output_folder}/Instructions.pdf"
}

# Split comma-separated values into arrays
IFS=',' read -ra experiment_type_array <<< "$experiment_types"
IFS=',' read -ra csv_file_array <<< "$csv_files"
IFS=',' read -ra json_file_array <<< "$json_files"

# Process each experiment type
for ((i=0; i<"${#experiment_type_array[@]}"; i++)); do
    process_experiment_type "${experiment_type_array[i]}" "${csv_file_array[i]}" "${json_file_array[i]}"
done