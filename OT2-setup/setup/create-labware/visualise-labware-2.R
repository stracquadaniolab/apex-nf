# visualise-labware-2.R

# This script generates plots for labware frames with wells based on CSV containing experiment data and corresponding labware JSON files.
library(ggplot2)
library(dplyr)
library(rjson)
library(ggforce)
library(tidyverse)

# This function reads and splits CSV data by different labwares determined by deck location
read_and_split_csv <- function(csv_file_path) {
  
  labware_name = "transformation-parameters"
  labware_file_path <- file.path("./data", paste0(labware_name, ".json")) # File path for the labware JSON file located in labware folder
  json_data <- fromJSON(file = labware_file_path)


  data <- read.csv(csv_file_path)

  # Create the volume column
  volume <- paste(data$dna_volume, "ul DNA,", data$cells_volume, "ul cells,", data$soc_volume, "ul SOC")

  # Create a new dataframe with desired columns
  labwares <- data.frame(
    well_name = data$transformation_well,
    dna_volume = data$dna_volume,
    cells_volume = data$cells_volume,
    soc_volume = data$soc_volume,
    volume = volume,
    reactant = volume,
    location = "thermocycler",
    labware = json_data$transformation_plate_name
  )

  split_labwares <- split(labwares, labwares$location)
  return(split_labwares)
}

# Function to check if the labware JSON file exists and if only one labware per deck is specified
check_labware_exists <- function(labware_name) {
  if (length(labware_name) > 1) {
    stop("There cannot be more than one plate on one deck.")
  }
  available_labware <- list.files(path = "./setup/create-labware/labware", pattern = ".json", full.names = FALSE)
  available_labware_names <- tools::file_path_sans_ext(available_labware)
  if (!labware_name %in% available_labware_names) {
    stop("The provided labware name does not match any available labware. If using custom labware, add the JSON file to the labware folder.")
  }
}

# This function gets the JSON file from the labware folder with all the dimensions of the specified labwares
get_labware_json <- function(labware_dataframe) {
  labware_name <- unique(labware_dataframe$labware)

  # check_labware_exists(labware_name) # Check if labware exists and if there is only one labware per deck
  labware_file_path <- file.path("./setup/create-labware/labware", paste0(labware_name, ".json")) # File path for the labware JSON file located in labware folder
  json_data <- fromJSON(file = labware_file_path)
  return(json_data)
}

# This function extracts well information from the JSON file
extract_well_info <- function(well) {
  # Determine the specific shape information based on the well shape
  shape_info <- switch(
    well$shape,
    rectangular = list(well_x_dim = well$xDimension, well_y_dim = well$yDimension), # For rectangular wells, extract x and y dimensions
    circular = list(diameter = well$diameter) # For circular wells, extract diameter
  )
  # Create a data frame containing well coordinates, shape, and shape-specific information
  data.frame(
    well_x_coord = well$x,
    well_y_coord = well$y,
    shape = well$shape, 
    shape_info
  )
}

# This function parses a JSON file containing labware information and extracts data for each well
parse_labware_json <- function(json_data) {
  # Apply the "extract_labware_json" function to get info for each well in the JSON file
  labware_data <- lapply(json_data$wells, extract_well_info) %>% 
    bind_rows(.id = "well_name") # Combine into one data frame by well_name as the id column
  return(labware_data)
}

# This function merges the labware data extracted from the JSON file with the CSV data based on the common well
map_wells_with_csv <- function(labware_data, csv_file) {
  # Merge labware data with CSV data based on the common well
  mapped_wells <- merge(labware_data, csv_file, by = "well_name", all.x = TRUE)
  return(mapped_wells)
}

# This function creates a labware frame to which later the wells are added.
plot_labware_frame <- function(merged_data, json_data, label, fill, title_size, legend_text_size, legend_key_size) {
  # Create a base plot for the plate frame with wells

  ggplot(merged_data, aes(well_x_coord, well_y_coord, fill = as.factor(!!rlang::sym(fill)), label = !!rlang::sym(label))) +
    geom_rect(
      aes(xmin = 0, xmax = json_data$dimensions$xDimension, ymin = 0, ymax = json_data$dimensions$yDimension), # Create a rectangle representing the plate frame
      fill = NA, color = "black", linewidth = 0.5
    ) +
    labs(title = paste(json_data$metadata$displayName, "in slot", unique(merged_data$location[!is.na(merged_data$location)]))) +
    theme_void() +
    theme(
      legend.position = "bottom",
      legend.direction = "vertical",
      legend.justification = "center",
      legend.box = "horizontal",
      legend.text = element_text(size = legend_text_size),
      legend.title = element_blank(),
      plot.title = element_text(size = title_size, hjust = 0.5)) +
    guides(fill = guide_legend(override.aes = list(size = legend_key_size)))
}

# This function adds rectangular wells to the existing labware frame
plot_rectangular_wells <- function(labware_frame, mapped_wells, max_y_wells, min_x_wells, label_size) {
  labware_frame + 
    geom_rect(
      aes(xmin = well_x_coord - well_x_dim/2, xmax = well_x_coord + well_x_dim - well_x_dim/2, ymin = well_y_coord - well_y_dim/2, ymax = well_y_coord + well_y_dim - well_y_dim/2),
      color = "black", size = 0.5
    ) +
    scale_fill_discrete(na.value = 'white', na.translate = FALSE) +
    geom_text(
      aes(x = well_x_coord, y = well_y_coord),
      size = label_size,
    ) +
    geom_text(
      data = max_y_wells,
      aes(x = well_x_coord, y = well_y_coord + well_y_dim),
      label = seq(1, nrow(max_y_wells)), size = 5
    ) +
    geom_text(
      data = min_x_wells,
      aes(x = well_x_coord - well_x_dim, y = well_y_coord),
      label = LETTERS[1:nrow(min_x_wells)], size = 5
    ) +
    coord_fixed() # Fix aspect ratio
}

# This function adds circular wells to the existing labware frame
plot_circular_wells <- function(labware_frame, mapped_wells, max_y_wells, min_x_wells, label_size) {
  labware_frame + 
    geom_point(
      aes(x = well_x_coord, y = well_y_coord),
      shape = 21, color = "black", size = mapped_wells$diameter*2.5
    ) +
    scale_fill_discrete(na.value = 'white', na.translate = FALSE) +
    geom_text(
      aes(x = well_x_coord, y = well_y_coord),
      size = label_size
    ) +
    geom_text(
      data = max_y_wells,
      aes(x = well_x_coord, y = well_y_coord + diameter),
      label = seq(1, nrow(max_y_wells)), size = 5
    ) +
    geom_text(
      data = min_x_wells,
      aes(x = well_x_coord - diameter, y = well_y_coord),
      label = LETTERS[1:nrow(min_x_wells)], size = 5
    ) +
    coord_fixed() # Fix aspect ratio
}

# This function creates the final labware plot, combining both the labware frame and wells
labware_plot <- function(mapped_wells, json_data, label, fill, title_size, label_size, legend_text_size, legend_key_size) {
  labware_frame <- plot_labware_frame(mapped_wells, json_data, label, fill, title_size, legend_text_size, legend_key_size) # Create the base plot for the plate frame with wells
  max_y_wells <- mapped_wells[mapped_wells$well_y_coord == max(mapped_wells$well_y_coord), ] %>% arrange(well_x_coord) # Extract wells with maximum y coordinates and arrange them by x coordinates (that is the first row to annotate with numbers)
  min_x_wells <- mapped_wells[mapped_wells$well_x_coord == min(mapped_wells$well_x_coord), ] %>% arrange(desc(well_y_coord)) # Extract wells with minimum x coordinates and arrange them by y coordinates (that is the first column t annotate with letters)
  
  # Determine the shape of the wells (rectangular or circular)
  shape <- unique(mapped_wells$shape)
  if (length(shape) > 1) {
    stop("Irregular shapes are not supported. All wells must have the same shape.")
  }
  
  if (shape == "rectangular") {
    plotted_labware <- plot_rectangular_wells(labware_frame, mapped_wells, max_y_wells, min_x_wells, label_size)
  } else if (shape == "circular") {
    plotted_labware <- plot_circular_wells(labware_frame, mapped_wells, max_y_wells, min_x_wells, label_size)
  }
  # Reorder reactant levels based on their appearance in the plot, so that the legend keys are in the correct order
  plotted_labware$data$reactant <- factor(plotted_labware$data$reactant, levels = unique(plotted_labware$data$reactant))
  return(plotted_labware)
}

# Main function to generate labware plots
generate_labware_plots <- function(csv_file_path, output_folder, label = "well_name", fill = "reactant", title_size, label_size, legend_text_size, legend_key_size, plot_width = 25, plot_height = 20, plot_units = "cm") {
  split_labwares <- read_and_split_csv(csv_file_path) # Create data frames for each unique labware-deck
  # For each labware data frame run the following functions:
  for (i in seq_along(split_labwares)) {
    labware_info <- get_labware_json(split_labwares[[i]])
    parsed_labware_info <- parse_labware_json(labware_info)
    mapped_wells_data <- map_wells_with_csv(parsed_labware_info, split_labwares[[i]])
    plotted_labware <- labware_plot(mapped_wells_data, labware_info, label, fill, title_size = 20, label_size = 5, legend_text_size = 20, legend_key_size = 10)

    # Extract unique reactants and create a filename
    deck_location <- unique(mapped_wells_data$location[!is.na(mapped_wells_data$location)])
    filename_suffix <- paste(deck_location, collapse = "-")

    # Save the plot with the corresponding filename
    output_file <- file.path(output_folder, paste0("slot", filename_suffix, "-labware.png"))
    ggsave(output_file, plotted_labware, width = plot_width, height = plot_height, units = plot_units, bg = "white")
  }
}

# Command-line arguments
args <- commandArgs(trailingOnly = TRUE)
csv_file_path <- args[1]
output_folder <- args[2]

# Generate labware plots
generate_labware_plots(csv_file_path, output_folder)
