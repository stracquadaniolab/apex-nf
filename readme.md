# enzyme-screening-platform-opentrons

![](https://img.shields.io/badge/current_version-0.1.0-blue)
![](https://github.com/stracquadaniolab/enzyme-screening-platform-opentrons/workflows/build/badge.svg)
## Overview
End-to-end eznyme screening platform for argB.

## Configuration

**Experiment parameters**
- `transformations_n`: number of transformations to be spotted (default: 24)
- `dna_volume`: volume of DNA in µL (default: 2)
- `cc_volume`: volume of competent cells in µL (default: 20)
- `soc_volume`: volume of SOC media in µL (default: 178)
- `competent_cells_well`: name of the well containing competent cells (defualt: "H12")
- `init_temp`: thermocycler inital temperature before heat-shock transformation (default: 4)
- `init_time`: thermocycler inital time before heat-shock transformation (default: 20)
- `heat_temp`: thermocycler heat temperature during heat-shock transformation (default: 42)
- `heat_time`: thermocycler heat temperature during heat-shock transformation (default: 1)
- `cool_temp`: thermocycler cooling temperature after heat-shock transformation (default: 4)
- `cool_time`: thermocycler cooling temperature after heat-shock transformation (default: 2)
- `inc_temp`: thermocycler incubation temperature after heat-shock transformation (default: 37)
- `inc_time`: thermocycler incubation temperature agter heat-shock transformation (default: 60)
- `spot_volume`: spot volume for agar plate in µL (default: 5)

**Hardware and labware names and location**
- `dna_plate_loadname`: name of the plate containing DNA to be transformed (default: "armadillo_96_wellplate_200ul_pcr_full_skirt")
- `dna_plate_slot`: 2
- `reservoir_loadname`: name of the reservoir containing SOC media and competent cells
- `reservoir_slot`: 3
- `transformation_plate_loadname`: name of the plate where transformation occurs (default: "armadillo_96_wellplate_200ul_pcr_full_skirt")
- `agar_plate_loadname`: name of the agar plate (default: "nunc_singlewell_plate_90ml_4x6_grid")
- `agar_def_json`: name of the json file with the custom agar plate definition (default: "nunc_singlewell_plate_90ml_4x6_grid")
- `agar_max_wells_n`: maximum number of wells on the agar plate (default: 24)
- `agar_slot`: location of the agar plates given as a list (default: [1])
- `p20_tiprack_loadname`: name of the p20 tiprack (default: "opentrons_96_tiprack_20ul")
- `p20_tiprack_slot`: location of the p20 tiprack (Default: 6)
- `p20_name`: name of the p20 pipette (default: "p20_single_gen2")
- `p20_mount`: location of the p20 pipette mount (default: "right")
- `p300_tiprack_loadname`: name of the p300 tiprack (default: "opentrons_96_tiprack_300ul")
- `p300_tiprack_slot`: location of the p300 tiprack (Default: 9)
- `p300_name`: name of the p300 pipette (default: "p300_multi_gen2")
- `p300_mount`: location of the p300 pipette mount (default: "left")


**Liquid handling settings**
- `dispense_rate`: dispense rate of the pipette while spotting in µL/sec (default: 60)
- `aspirate_rate`: spirate rate of the pipette while spotting in µL/sec (default: 60)
- `dispense_height`: height at which the piepette dispenses above the bottom of the plate in mm (default: 10.2)

**Optional**
- `test_dispense_height`: test for the dispense height above the agar plate (default: true)
- `test_dispense_height`:
- `agar_incubation`: agar plate incubation in place on the temperature module (default: false)
- `temp_mod_slot`: (default: 4)
- `agar_incubation_temp`: set the incubation temperature for the temperature module in celsius (default: 37)


### Opentrons OT2 deck

|          |           |           | 
| ---------| --------- | --------- |
|  10      |  11       |  12       |
|  7       |  8        |  9        |
|  4       |  5        |  6        |
|  1       |  2        |  3        |


### Simulate the protocol

```bash
opentrons_simulate protocol.py -e -o nothing
```

## Authors

- Martyna Kasprzyk
