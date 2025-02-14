# Finale to MusicXML Converter

[![GitHub](https://img.shields.io/github/stars/joris-vaneyghen/musx2mxl?style=social)](https://github.com/joris-vaneyghen/musx2mxl)

## About
This project is a private initiative aimed at musicians and composers who no longer have a valid Finale license and have no other alternative than the built-in Finale export function. This converter allows users to transform **Finale (.musx) music scores** into **MusicXML (.mxl) format**, making it possible to import them into various music notation software.

**Note:** This converter currently supports only **basic notations** and does not guarantee the exact preservation of bar positions, note placements, and other advanced notations. It is still a **work in progress**.


## Online File Converter

Easily convert Finale `.musx` files to `.mxl` format online.

**[online musx2xml converter](https://jorisvaneyghen-musx2mxl.hf.space/)**.

![Online Converter](images/online-converter.png)

## Run Online File Converter Locally Using Docker
You can run the online converter on your own machine using Docker.

### Prerequisites
Make sure you have the following installed:
- **Docker** ([Install Docker](https://docs.docker.com/get-docker/))

### Running the Converter
```sh
docker run -it -p 7860:7860 --platform=linux/amd64 \
    registry.hf.space/jorisvaneyghen-musx2mxl:latest python app.py
```
After running the command, open your web browser and go to: [http://localhost:7860/](http://localhost:7860/)

For implementation details, check the **[Git repository](https://huggingface.co/spaces/jorisvaneyghen/musx2mxl/tree/main)**.



## Installation

### Prerequisites
Make sure you have the following installed:
- **Python 3** ([Install Python](https://www.python.org/downloads/))
- **pip** (comes with Python but can be updated via `python -m ensurepip` or `python -m pip install --upgrade pip`)

### Install

To install the required package on your local system:
```sh
pip install musx2mxl
```

##  Usage

### Graphical Interface (GUI)
Run the GUI version with following command in console:
```sh
musx2mxl-gui
```
![GUI Screenshot](images/musx2mxl-gui.png)

### Command Line Execution (Batch Processing)
You can also run the converter via the command line:
```sh
musx2mxl [options] input_path
```

#### 🔹 Arguments
```
  input_path        A Finale file (*.musx) or a directory containing several Finale files.
```

#### 🔹 Options
```
  -h, --help        Show this help message and exit.
  --output_path     Specify the output .mxl file path (default: same as input but with .mxl extension). Ignored if input_path is a directory.
  --keep            Keep the decoded Finale data (*.enigmaxml) and uncompressed MusicXML (*.musicxml).
  --recursive       Scan subdirectories recursively if input_path is a directory.
```

## Supported Music Notation Software
MusicXML is a widely used format, and many music notation programs support importing it, including:
- **MuseScore** (https://musescore.org)
- **Sibelius** (https://www.avid.com/sibelius)
- **Dorico** (https://www.steinberg.net/dorico)
- **Notion** (https://www.presonus.com/products/Notion)
- **Capella** (https://www.capella-software.com)

For more details about MusicXML, visit: **[MusicXML Official Website](https://www.musicxml.com)**

## Implementation
The development of this converter is based on earlier work from the following open-source projects:
- **MUSX Document Model ([Robert G. Patterson](https://robertgpatterson.com)):** [GitHub Repository](https://github.com/rpatters1/musxdom)
- **Project-Attacca:** [GitHub Repository](https://github.com/Project-Attacca/enigmaxml-documentation)
- **Denigma:** [GitHub Repository](https://github.com/chrisroode/denigma)

## Disclaimer
This project is not affiliated with **Finale** or **MakeMusic** in any way. For official Finale software and support, please visit: **[Finale Official Website](https://www.finalemusic.com)**.

## License
This project is licensed under the **MIT License**, allowing free use, modification, and distribution. See the LICENSE file for more details.

