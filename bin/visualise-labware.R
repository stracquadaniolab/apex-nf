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
  df$location <- factor(df$location, levels = unique(df$location))
  split(df, df$location)
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
  shape_info <- switch(
    well$shape,
    rectangular = list(well_x_dim = well$xDimension, well_y_dim = well$yDimension),
    circular = list(diameter = well$diameter)
  )
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
  # Preserve original id order
  if ("id" %in% colnames(experiment_data)) {
    original_id_order <- unique(experiment_data$id)
  }
  
  merged_data <- merge(well_data, experiment_data, by = "well_name", all.x = TRUE)
  
  # Set factor levels based on original order
  if (exists("original_id_order") && "id" %in% colnames(merged_data)) {
    merged_data$id <- factor(merged_data$id, levels = original_id_order)
  }
  
  return(merged_data)
}

# Creates the base plot with plate outline and title
plot_labware_frame <- function(merged_data, json_data, label, fill, title_size, legend_text_size, legend_key_size, legend_row_number) {
  n_items <- length(unique(merged_data[[fill]]))
  
  # Dynamic legend layout calculation
  if (n_items > 12) {
    if (n_items > 60) {
      optimal_cols <- 8
    } else if (n_items > 30) {
      optimal_cols <- 6
    } else {
      optimal_cols <- 5
    }
    legend_row_number <- ceiling(n_items / optimal_cols)
  }
  
  # Scale sizes for larger plates
  adjusted_title_size <- title_size
  adjusted_legend_text_size <- legend_text_size 
  adjusted_legend_key_size <- legend_key_size
  
  if (n_items > 60) {
    adjusted_title_size <- title_size * 0.8
    adjusted_legend_text_size <- legend_text_size * 0.8
    adjusted_legend_key_size <- legend_key_size * 0.8
  } else if (n_items > 30) {
    adjusted_title_size <- title_size * 0.9
    adjusted_legend_text_size <- legend_text_size * 0.9
    adjusted_legend_key_size <- legend_key_size * 0.9
  }
  
  if (!is.factor(merged_data[[fill]])) {
    merged_data[[fill]] <- factor(merged_data[[fill]], levels = unique(merged_data[[fill]]))
  }

  ggplot(merged_data, aes(well_x_coord, well_y_coord, fill = as.factor(!!rlang::sym(fill)), label = !!rlang::sym(label))) +
    geom_rect(
      aes(xmin = 0, xmax = json_data$dimensions$xDimension, ymin = 0, ymax = json_data$dimensions$yDimension),
      fill = NA, color = "black", linewidth = 0.5
    ) +
    labs(title = paste(json_data$metadata$displayName, "in slot", unique(merged_data$location[!is.na(merged_data$location)]))) +
    theme_void() +
    theme(
      legend.position = "bottom",
      legend.justification = "center",
      legend.text = element_text(size = adjusted_legend_text_size),
      legend.title = element_blank(),
      legend.box = "horizontal",
      legend.spacing.x = unit(0.3, "cm"),
      legend.spacing.y = unit(0.2, "cm"),
      legend.margin = margin(2, 2, 2, 2),
      plot.margin = margin(15, 15, 40, 15),
      plot.title = element_text(size = adjusted_title_size, hjust = 0.5)
    ) +
    guides(fill = guide_legend(
      ncol = ifelse(n_items > 12, optimal_cols, 4),
      byrow = TRUE,
      override.aes = list(size = adjusted_legend_key_size),
      keywidth = unit(adjusted_legend_key_size * 0.9, "pt"),
      keyheight = unit(adjusted_legend_key_size * 0.9, "pt"),
      drop = FALSE
    ))
}

# Plots rectangular wells with position labels
plot_rectangular_wells <- function(labware_frame, mapped_wells, max_y_wells, min_x_wells, label_size, labware_json) {
  # Calculate margins and labels
  plate_width <- labware_json$dimensions$xDimension
  plate_height <- labware_json$dimensions$yDimension
  
  top_well_ymax <- max(mapped_wells$well_y_coord + mapped_wells$well_y_dim/2)
  left_well_xmin <- min(mapped_wells$well_x_coord - mapped_wells$well_x_dim/2)
  
  top_margin <- plate_height - top_well_ymax
  left_margin <- left_well_xmin
  
  # Extract column positions
  well_positions <- data.frame(
    well_name = mapped_wells$well_name,
    x_coord = mapped_wells$well_x_coord
  )
  
  well_positions$col_num <- as.numeric(gsub("^[A-Za-z]+", "", well_positions$well_name))
  
  col_to_x <- well_positions %>%
    select(col_num, x_coord) %>%
    distinct() %>%
    arrange(col_num)
  
  # Create label positions
  column_labels <- data.frame(
    x = col_to_x$x_coord,
    y = plate_height - (top_margin / 2),
    label = col_to_x$col_num
  )
  
  row_labels <- data.frame(
    x = left_margin / 2,
    y = unique(mapped_wells$well_y_coord[order(mapped_wells$well_name)]),
    label = LETTERS[1:length(unique(mapped_wells$well_y_coord))]
  )
  
  # Generate plot
  labware_frame +
    geom_rect(
      aes(xmin = well_x_coord - well_x_dim/2, xmax = well_x_coord + well_x_dim - well_x_dim/2, 
          ymin = well_y_coord - well_y_dim/2, ymax = well_y_coord + well_y_dim - well_y_dim/2),
      color = "black", size = 0.5
    ) +
    scale_fill_discrete(na.value = "white", na.translate = FALSE, drop = FALSE) +
    geom_text(
      aes(x = well_x_coord, y = well_y_coord),
      size = label_size
    ) +
    geom_text(
      data = column_labels,
      aes(x = x, y = y, label = label),
      size = 5, inherit.aes = FALSE
    ) +
    geom_text(
      data = row_labels,
      aes(x = x, y = y, label = label),
      size = 5, inherit.aes = FALSE
    ) +
    coord_fixed()
}

# Plots circular wells with position labels
plot_circular_wells <- function(labware_frame, mapped_wells, max_y_wells, min_x_wells, label_size, labware_json) {
  # Calculate margins and labels
  plate_width <- labware_json$dimensions$xDimension
  plate_height <- labware_json$dimensions$yDimension
  
  top_well_radius <- max_y_wells$diameter / 2
  left_well_radius <- min_x_wells$diameter / 2
  top_well_ymax <- max(mapped_wells$well_y_coord) + top_well_radius
  left_well_xmin <- min(mapped_wells$well_x_coord) - left_well_radius
  
  top_margin <- max(plate_height - top_well_ymax, 5)
  left_margin <- max(left_well_xmin, 5)
  
  # Extract column positions
  well_positions <- data.frame(
    well_name = mapped_wells$well_name,
    x_coord = mapped_wells$well_x_coord
  )
  
  well_positions$col_num <- as.numeric(gsub("^[A-Za-z]+", "", well_positions$well_name))
  
  col_to_x <- well_positions %>%
    select(col_num, x_coord) %>%
    distinct() %>%
    arrange(col_num)
  
  # Create label positions
  column_labels <- data.frame(
    x = col_to_x$x_coord,
    y = plate_height - (top_margin / 2),
    label = col_to_x$col_num
  )
  
  row_labels <- data.frame(
    x = left_margin / 2,
    y = unique(mapped_wells$well_y_coord[order(mapped_wells$well_name)]),
    label = LETTERS[1:length(unique(mapped_wells$well_y_coord))]
  )
  
  # Generate plot
  labware_frame +
    geom_point(
      aes(x = well_x_coord, y = well_y_coord),
      shape = 21, color = "black", size = mapped_wells$diameter*2.5
    ) +
    scale_fill_discrete(na.value = "white", na.translate = FALSE, drop = FALSE) +
    geom_text(
      aes(x = well_x_coord, y = well_y_coord),
      size = label_size
    ) +
    geom_text(
      data = column_labels,
      aes(x = x, y = y, label = label),
      size = 5, inherit.aes = FALSE
    ) +
    geom_text(
      data = row_labels,
      aes(x = x, y = y, label = label),
      size = 5, inherit.aes = FALSE
    ) +
    coord_fixed()
}

# Creates the complete labware plot with wells
labware_plot <- function(mapped_wells, json_data, label, fill, title_size, label_size, legend_text_size, legend_key_size, legend_row_number) {
  labware_frame <- plot_labware_frame(mapped_wells, json_data, label, fill, title_size, legend_text_size, legend_key_size, legend_row_number)
  
  max_y_wells <- mapped_wells[mapped_wells$well_y_coord == max(mapped_wells$well_y_coord), ] %>% arrange(well_x_coord)
  min_x_wells <- mapped_wells[mapped_wells$well_x_coord == min(mapped_wells$well_x_coord), ] %>% arrange(desc(well_y_coord))
  
  shape <- unique(mapped_wells$shape)
  if (length(shape) > 1) {
    stop("Irregular shapes are not supported. All wells must have the same shape.")
  }
  
  if (shape == "rectangular") {
    plotted_labware <- plot_rectangular_wells(labware_frame, mapped_wells, max_y_wells, min_x_wells, label_size, json_data)
  } else if (shape == "circular") {
    plotted_labware <- plot_circular_wells(labware_frame, mapped_wells, max_y_wells, min_x_wells, label_size, json_data)
  }
  
  # Preserve factor levels
  if ("id" %in% colnames(plotted_labware$data) && is.factor(mapped_wells[[fill]])) {
    plotted_labware$data$id <- factor(plotted_labware$data$id, levels = levels(mapped_wells[[fill]]))
  } else {
    plotted_labware$data$id <- factor(plotted_labware$data$id, levels = unique(plotted_labware$data$id))
  }
  
  return(plotted_labware)
}

# Main function to generate labware plots
generate_labware_plots <- function(csv_file_path, opentrons_labware_directory, plot_params = list()) {
  counter <- 0
  
  split_csv_by_location(csv_file_path) %>%
    map(~{
        counter <- counter + 1
        counter_value <- sprintf("%02d", counter)
        
        labware_details <- get_labware_details(opentrons_labware_directory, .x)
        well_data <- process_labware_json_for_plotting(labware_details)
        combined_data <- combine_well_and_experiment_data(well_data, .x)
        
        # Adjust dimensions based on legend size
        n_fill_values <- length(unique(combined_data[[plot_params$fill]]))
        plot_width <- plot_params$plot_width
        plot_height <- plot_params$plot_height
        
        if (n_fill_values > 60) {
          rows_needed <- ceiling(n_fill_values / 8)
          plot_height <- plot_height + min(10, rows_needed * 0.7)
          plot_width <- min(28, plot_width)
        } else if (n_fill_values > 30) {
          rows_needed <- ceiling(n_fill_values / 6)
          plot_height <- plot_height + min(6, rows_needed * 0.6)
          plot_width <- min(26, plot_width)
        }
        
        plotted_labware <- labware_plot(combined_data, labware_details, plot_params$label, 
                           plot_params$fill, plot_params$title_size, plot_params$label_size, 
                           plot_params$legend_text_size, plot_params$legend_key_size, 
                           plot_params$legend_row_number)
        
        deck_location <- unique(combined_data$location[!is.na(combined_data$location)])
        filename_suffix <- paste(deck_location, collapse = "-")
        output_file <- paste0("plots/", counter_value, "-slot-", filename_suffix, "-labware.png")
        
        ggsave(output_file, plotted_labware, width = plot_width, 
               height = plot_height, units = plot_params$plot_units, 
               bg = "white", dpi = 150)
    })
}

# Process command-line arguments
args <- commandArgs(trailingOnly = TRUE)
csv_path <- args[1]
opentrons_labware_directory <- args[2]

plot_params <- list(label = "volume", fill = "id", title_size = 14, label_size = 4, 
                   legend_text_size = 10, legend_key_size = 10, legend_row_number = 2, 
                   plot_width = 25, plot_height = 20, plot_units = "cm")

# Generate plots
generate_labware_plots(csv_path, opentrons_labware_directory, plot_params)