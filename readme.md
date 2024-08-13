# apex-nf: Automated Protein EXpression in E. coli

![](https://img.shields.io/badge/current_version-0.3.2-blue)
![](https://github.com/stracquadaniolab/apex-nf/workflows/build/badge.svg)

## Overview
APEX pipeline consists of a series of automated *E. coli* laboratory protocols for protein expression:
1. **Heat Shock Transformation**
2. **Colony Selection**
3. **Colony Sampling**
4. **Protein Expression Induction**

Manual providing detailed instructions for using APEX can be found here. 
A comprehensive user manual detailing the setup, configuration, and operation of the APEX pipeline is available [here](./APEX-manual.pdf).

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
that it works the same way on any system.


## Run the pipeline

To run the pipeline execute this command in your CLI:

```
nextflow run stracquadaniolab/apex-nf
```

Before running the `stracquadaniolab/apex-nf`, you need to prepare JSON and CSV files corresponding to each protocol. Examples can be found [here](./assets/testdata/).



## Team
- Martyna Kasprzyk (Principal developer and Maintainer)
- Giovanni Stracquadanio (Principal Investigator)