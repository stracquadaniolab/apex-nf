#!/usr/bin/env Rscript

library(rjson)
library(gridExtra)
library(grid)
library(png)

insert_overview <- function(data, x_margin, y_initial, y_spacing, font_size) {
  grid.text("Induction of protein expression in OT-2", x = x_margin, y = y_initial, just = "left", gp = gpar(fontsize = font_size + 4, fontface = "bold"))
  overview <- c("Quick Overview",
                paste("Once the cultures have reached the desired growth phase, the robot transfers cells to appropriate plates."),
                paste("The robot adds an inducer to the cultures."),
                paste("After induction, cultures are incubated to allow for protein expression."))
  overview_y_lines <- (y_initial - 2*y_spacing) - seq(0, length(overview) - 1) * y_spacing
  text_style <- gpar(fontsize = font_size, fontface = c("bold", rep("plain", length(overview) - 1)))
  grid.text(overview, x = x_margin, y = overview_y_lines, just = "left", gp = text_style)
  return(overview_y_lines[length(overview_y_lines)]-y_spacing)
}

insert_preparation <- function(x_margin, y_initial, y_spacing) {
  preparation <- c("Preparation",
                   "Prepare the reagents and labware according to the below diagrams.",
                   "Volumes (uL) indicate how much of reagents will be used, so add additional volume.")

  preparation_y_lines <- y_initial - y_spacing * (1:length(preparation))
  text_style <- gpar(fontsize = 12, fontface = c("bold", rep("plain", length(preparation) - 1)))
  grid.text(preparation, x = x_margin, y = preparation_y_lines, just = "left", gp = text_style)
  return(preparation_y_lines[length(preparation_y_lines)]-y_spacing)
}

insert_labware <- function(visualised_labware, width, height, x_margin, y_initial, y_spacing) {
  image_files <- list.files(visualised_labware, pattern = "^0", full.names = TRUE)
  num_images <- length(image_files)

  positions <- list()
  # Generate positions
  for (i in 1:num_images) {
    # Calculate position based on index
    x <- x_margin + width/2 + ((i - 1) %% 2) * width
    y <- y_initial - height/2 + floor((i - 1) / 2) * - height
    positions[[i]] <- list(x = x, y = y)
  }
    # Insert each image into the PDF
  for (i in seq_along(image_files)) {
    if (file.exists(image_files[i])) {
      image <- readPNG(image_files[i])
      position <- positions[[i]]
      grid.raster(image, x = position$x, y = position$y, width = width, height = height)
    }
  }
  
  return(positions[[num_images]]$y - height/2 - y_spacing)
}

insert_deck_loading <- function(data, x_margin, y_initial, font_size, y_spacing) {
  deck <- c("Deck Loading Instructions",
                paste("Check that", data$right_pipette_name, "is in the right mount, and", data$left_pipette_name, "is in the left mount." ),
                paste("Slot", paste(data$right_pipette_tiprack_slot, collapse = ", "), ": load", data$right_pipette_tiprack_name, "for the", data$right_pipette_name, "pipette."),
                paste("Slot", paste(data$left_pipette_tiprack_slot, collapse = ", "), ": load", data$left_pipette_tiprack_name, "for the", data$left_pipette_name, "pipette."),
                paste("Slot", data$blank_plate_slot, ": load", data$blank_plate_name, "containing blank for the plate reader."),
                paste("Slot", data$culture_plate_slot, ": load", data$culture_plate_name, "containing the cell culture."),
                paste("Slot", data$inducer_plate_slot, ": load", data$inducer_plate_name, "containing the inducer."),
                paste("Slot", data$destination_plate_slot, ": load", data$destination_plate_name, " where the induction occurs."))
  deck_y_lines <- y_initial - seq(0, length(deck) - 1) * y_spacing
  text_style <- gpar(fontsize = font_size, fontface = c("bold", rep("plain", length(deck) - 1)))
  grid.text(deck, x = x_margin, y = deck_y_lines, just = "left", gp = text_style)
}

instructions <- function(json_file_path, visualised_labware, output_file, x_margin = 0.05, y_spacing = 0.02, labware_width = 0.45, labware_height = 0.27, font_size = 12, y_initial = 0.98) {
  pdf(output_file, width = 8.5, height = 11)
  par(mar = c(5, 4, 4, 2) + 0.1)
  json_data <- fromJSON(file = json_file_path)

  overview <- insert_overview(json_data, x_margin, y_initial, y_spacing, font_size) # Title and Overview
  preparation <- insert_preparation(x_margin, overview, y_spacing)   # Reagents preparation

  labware <- insert_labware(visualised_labware, labware_width, labware_height, x_margin, preparation, y_spacing)   # # Insert images and get coordinates
  deck_loading <- insert_deck_loading(json_data, x_margin, labware, font_size, y_spacing)

  dev.off()
  
}

# Command-line arguments
args <- commandArgs(trailingOnly = TRUE)
json_file_path <- args[1]
visualised_labware <- args[2]
output_file <- args[3]

# Generateinstructions
instructions(json_file_path, visualised_labware, output_file)
