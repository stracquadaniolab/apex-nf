# apex-nf: Automated Protein EXpression in E. coli

![](https://img.shields.io/badge/current_version-0.3.2-blue)
![](https://github.com/stracquadaniolab/apex-nf/workflows/build/badge.svg)

## Overview

This manual provides instructions for using the Opentrons Protein Screening
Pipeline, which is written in Nextflow and shared on GitHub. The pipeline
consists of a seres of automated E. coli laboratory protocols including:
heat-shock transformations (Protocol 1), agar plate spotting (Protocol 2),
colony sampling (Protocol 3), and protein expression induction (Protocol4).

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Protocol 1: Transformation](#protocol-1-transformation)
4. [Protocol 2: Spotting](#protocol-2-spotting)
5. [Protocol 3: Colony Sampling](#protocol-3-colony-sampling)
6. [Protocol 4: Induction](#protocol-4-induction)
7. [Running the Full Screening Pipeline](#running-the-full-screening-pipeline)
8. [Output](#output)

## System Requirements

- **Operating System:** Compatible with Windows, macOS, or Linux.
- **Software:** 
    - **Nextflow:** A workflow management system. Install it from [Nextflow's
      website](https://www.nextflow.io/).
    - Access to a Command Line Interface (CLI).

## Installation

To set up the `stracquadniolab/apex-nf`, open your Terminal or Command Prompt
and execute:

```
nextflow pull stracquadniolab/apex-nf
```

This command downloads and sets up the `stracquadniolab/apex-nf` on your system.
After installing the `stracquadniolab/apex-nf`, a Docker image containing all
necessary packages, including the Opentrons runtime, will be downloaded. Docker
containers provide a consistent environment for the software to run, ensuring
that it works the same way on any system. This allows for the pipeline to run
the workflows effortlessly.


## Run the pipeline

To run the pipeline execute this command in your CLI:

```
nextflow run stracquadaniolab/apex-nf
```

Before running the `stracquadaniolab/apex-nf`, you need to prepare JSON and CSV files corresponding to each protocol. Below, you can find the format for each file, and examples can be found in the "testdata" folder. Note that if a parameter is enclosed in quotation marks (e.g., `"p20_multi_gen2"`), you should include it exactly as shown. If a parameter is enclosed in brackets (e.g., `[2, 3]`), you should include it as a list, separated by commas if there are multiple values, even if there is only one value (e.g., `[2]`).

## Protocol 1: Heat-shock Transformation

### JSON Configuration File

| Parameter                        | Description                                                                            | Example                                            |
|----------------------------------|----------------------------------------------------------------------------------------|----------------------------------------------------|
| `right_pipette_name`             | Defines the model of the right pipette.                                                | `"p20_multi_gen2"`                                 |
| `right_pipette_tiprack_name`     | Defines the name of the right pipette's tip racks.                                     | `"opentrons_96_tiprack_20ul`                       |
| `right_pipette_tiprack_slot`     | Defines the slots on the deck where the right pipette's tip racks are placed.          | `[2, 3]`                                           |
| `left_pipette_name`              | Defines the model of the left pipette.                                                 | `"p300_multi_gen2"`                                |
| `left_pipette_tiprack_name`      | Defines the name of the left pipette's tip racks.                                      | `"opentrons_96_tiprack_20ul`                       |
| `left_pipette_tiprack_slot`      | Defines the slots on the deck where the left pipette's tip racks are located.          | `[6, 9]`                                           |
| `dna_plate_name`                 | Defines the type of plate containing DNA.                                              | `"armadillo_96_wellplate_200ul_pcr_full_skirt"`    |
| `dna_plate_slot`                 | Defines the deck slot for the plate containing DNA.                                    | `1`                                                |
| `cells_plate_name`               | Defines the type of plate containing competent cells.                                  | `"armadillo_96_wellplate_200ul_pcr_full_skirt"`    |
| `cells_plate_slot`               | Defines the deck slot for the plate containing cells.                                  | `1`                                                |
| `media_plate_name`               | Defines the type of plate containing media.                                            | `"armadillo_96_wellplate_200ul_pcr_full_skirt"`    |
| `media_plate_slot`               | Defines the deck slot for the plate containing media.                                  | `1`                                                |
| `destination_plate_name`      | Defines the type of plate used for the transformation (compatible with thermocycler).  | `"armadillo_96_wellplate_200ul_pcr_full_skirt"`    |
| `init_temp`                      | Set the initial cooling incubation temperature (Celcius degrees).                      | `4`                                                |
| `init_time`                      | Set the duration for the initial cooling incubation (minutes).                         | `20`                                               |
| `heat_temp`                      | Set the temperature for the heat-shock (Celcius degrees).                              | `42`                                               |
| `heat_time`                      | Set the duration for the heat-shock (seconds).                                         | `30`                                               |
| `cool_temp`                      | Set the temperature for the post heat-shock cooling incubation (Celcius degrees).      | `4`                                                |
| `cool_time`                      | Set the duration for the post heat-shock cooling incubation (minutes).                 | `2`                                                |
| `inc_temp`                       | Set the temperature for the recovery incubation (Celcius degrees).                     | `37`                                               |
| `inc_time`                       | Set the duration for the recovery incubation (minutes).                                | `60`                                               |

### CSV Configuration File

| Parameter     | Description                                                                     | Example    |
|---------------|---------------------------------------------------------------------------------|------------|
| `dna_id`      | Identifier for the DNA sample.                                                  | `pUC19`    |
| `dna_well`    | Well location of the DNA sample on the plate specified in JSON file.            | `A1`       |
| `dna_volume`  | Volume of DNA used for transformation (µL).                                     | `1`        |
| `cells_id`    | Identifier for the competents cells sample.                                     | `DH5a`     |
| `cells_well`  | Well location of the competent cells on the plate specified in JSON file.       | `A2`       |
| `cells_volume`| Volume of competent cells to be transformed (µL).                               | `10`       |
| `media_id`    | Identifier for the media used.                                                  | `SOC`      |
| `media_well`  | Well location of the media on the plate specified in the JSON file.             | `A3`       |
| `media_volume`| Volume of media used for recovery (µL).                                         | `50`       |


## Protocol 2: Agar plate spotting

### JSON Configuration File

| Parameter                        | Description                                                                                                             | Example                                          |
|----------------------------------|-------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------|
| `pipette_name`                   | Model of the pipette used for spotting.                                                                                 | `"p20_multi_gen2"`                               |
| `pipette_mount`                  | Specifies which side of the robot the pipette is mounted on (left or right).                                            | `"right"`                                        |
| `tiprack_name`                   | Name of the pipette's tip racks.                                                                                        | `"opentrons_96_tiprack_20ul`                     |
| `tiprack_slots`                   | Defines the deck slot where the pipette's tip racks are placed.                                                         | `[2, 3]`                                         |
| `source_plate_name`              | Specifies the type of plate containing the source material, i.e. transformed cells.                                     | `"armadillo_96_wellplate_200ul_pcr_full_skirt"`  |
| `source_plate_slot`              | Defines the deck slot for the source plate.                                                                             | `"thermocycler"`                                 |
| `agar_plate_name`                | Specifies the type of agar plate.                                                                                       | `"nunc96grid_96_wellplate_10ul"`                 |
| `agar_plate_slots`                | Defines the deck slot for the agar plates.                                                                              | `[1]`                                            |
| `agar_plate_area`                | The base area of the agar plate (mm<sup>2</sup>).                                                                       | `9469.2`                                         |
| `empty_agar_plate_weight`        | The weight of the empty plate without agar (g).                                                                         | `38.92`                                          |
| `agar_density`                   | Density of the agar (g mm<sup>-3</sup>).                                                                                | `0.0008975`                                      |
| `spotting_volume`                | Volume that is dispensed during the spotting process (&mu;L).                                                           | `5`                                              |
| `additional_volume`              | Specifies any additional volume that is added to the spotting volume but not dispensed (&mu;L).                         | `1`                                              |
| `spotting_height`                | Sets the height relative to the agar surface for spotting, where a negative value indicates pipette piercing the agar.  | `0`                                              |


### CSV Configuration File

| Parameter              | Description                                                                   | Example       |
|------------------------|-------------------------------------------------------------------------------|---------------|
| `id`                   | Identifier for the sample.                                                    | `pUC19-DH5a`  |
| `agar_plate_location`  | Defines the deck slot for the agar plate specified in JSON file.              | `1`           |
| `source_well`          | Well location on the source plate from which transformed cells are aspirated. | `A1`          |
| `destination_well`     | Well location on the agar plate where the transformed cells will be spotted.  | `A1`          |
| `agar_plate_weight`    | Weight of the plate with agar (g).                                            | `77.12`       |


## Team
- Martyna Kasprzyk (Principal developer and Maintainer)
- Giovanni Stracquadanio (Principal Investigator)