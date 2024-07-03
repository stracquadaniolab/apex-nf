#!/usr/bin/env Rscript

# This script generates plots for labware frames with wells based on CSV containing experiment data and corresponding labware JSON files.
library(rjson)
library(ggplot2)
library(dplyr)
library(purrr)

# Ensure output directory exists
if (!file.exists("plots")) {
  dir.create("plots")
}

# Reads CSV data, splits it by "location" to handle different labware types
split_csv_by_location <- function(csv_file_path) {
  df <- read.csv(csv_file_path)
  df$location <- factor(df$location, levels = unique(df$location)) # Order "location" factor levels by their appearance in the dataset
  split(df, df$location) # Split the data frame into a list of data frames, one per location
}

# Checks if the specified labware's JSON file exists in the Opentrons labware directory
validate_labware_exists <- function(labware_name, opentrons_labware) {
  if (length(labware_name) != 1) {
    stop("Each deck must have exactly one labware type.")
  }
  available_labware <- list.files(path = opentrons_labware, pattern = "\\.json$", full.names = FALSE) %>%
    tools::file_path_sans_ext()

  if (!labware_name %in% available_labware) {
    stop("Labware name does not match available labware. Add custom JSON if necessary.")
  }
}

# Retrieves and decodes the labware's JSON data
get_labware_details <- function(opentrons_labware, labware_dataframe) {
  labware_name <- unique(labware_dataframe$labware)
  validate_labware_exists(labware_name, opentrons_labware)
  fromJSON(file = file.path(opentrons_labware, paste0(labware_name, ".json")))
}

# Extracts well information from a labware JSON
extract_well_details <- function(well) {
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

# Processes labware JSON to extract detailed data for plotting
process_labware_json_for_plotting <- function(json_data) {
  map_df(json_data$wells, extract_well_details, .id = "well_name")
}

# Combines well data from JSON with experimental data from CSV
combine_well_and_experiment_data <- function(well_data, experiment_data) {
  merge(well_data, experiment_data, by = "well_name", all.x = TRUE)
}

# This function creates a labware frame to which later the wells are added.
plot_labware_frame <- function(merged_data, json_data, label, fill, title_size, legend_text_size, legend_key_size, legend_row_number) {
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
      legend.justification = "center",
      legend.text = element_text(size = legend_text_size),
      legend.title = element_blank(),
      plot.title = element_text(size = title_size, hjust = 0.5)) +
    guides(fill = guide_legend(nrow = legend_row_number, override.aes = list(size = legend_key_size)))
}

# This function adds rectangular wells to the existing labware frame
plot_rectangular_wells <- function(labware_frame, mapped_wells, max_y_wells, min_x_wells, label_size) {
  labware_frame +
    geom_rect(
      aes(xmin = well_x_coord - well_x_dim/2, xmax = well_x_coord + well_x_dim - well_x_dim/2, ymin = well_y_coord - well_y_dim/2, ymax = well_y_coord + well_y_dim - well_y_dim/2),
      color = "black", size = 0.5
    ) +
    scale_fill_discrete(na.value = "white", na.translate = FALSE) +
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
    scale_fill_discrete(na.value = "white", na.translate = FALSE) +
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
labware_plot <- function(mapped_wells, json_data, label, fill, title_size, label_size, legend_text_size, legend_key_size, legend_row_number) {
  labware_frame <- plot_labware_frame(mapped_wells, json_data, label, fill, title_size, legend_text_size, legend_key_size, legend_row_number) # Create the base plot for the plate frame with wells
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
  plotted_labware$data$id <- factor(plotted_labware$data$id, levels = unique(plotted_labware$data$id))
  return(plotted_labware)
}

counter_env <- new.env()
counter_env$counter <- 0
# Main function to generate labware plots
generate_labware_plots <- function(csv_file_path, opentrons_labware_directory, plot_params = list()) {
  split_csv_by_location(csv_file_path) %>%
    map(~{
        # Increment and retrieve the counter
        print(.x)
        counter_env$counter <- counter_env$counter + 1
        counter_value <- sprintf("%02d", counter_env$counter) # Format the counter with leading zeros
        
        labware_details <- get_labware_details(opentrons_labware_directory, .x)
        well_data <- process_labware_json_for_plotting(labware_details)
        combined_data <- combine_well_and_experiment_data(well_data, .x)
        plotted_labware <- labware_plot(combined_data, labware_details, plot_params$label, plot_params$fill, plot_params$title_size, plot_params$label_size, plot_params$legend_text_size, plot_params$legend_key_size, plot_params$legend_row_number)
        
        deck_location <- unique(combined_data$location[!is.na(combined_data$location)]) # Extract the location and create a filename
        filename_suffix <- paste(deck_location, collapse = "-")
        output_file <- paste0("plots/", counter_value, "-slot-", filename_suffix, "-labware.png")
        ggsave(output_file, plotted_labware, width = plot_params$plot_width, height = plot_params$plot_height, units = plot_params$plot_units, bg = "white")
    })
}

# Command-line arguments processing
args <- commandArgs(trailingOnly = TRUE)
csv_path <- args[1]
opentrons_labware_directory <- args[2]

# Default plotting parameters, could be extended to parse additional CLI arguments
plot_params <- list(label = "volume", fill = "id", title_size = 20, label_size = 4, legend_text_size = 16, legend_key_size = 10, legend_row_number = 3, plot_width = 25, plot_height = 20, plot_units = "cm")

# Initiate plot generation
generate_labware_plots(csv_path, opentrons_labware_directory, plot_params)