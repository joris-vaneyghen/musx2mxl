# Finale to MusicXML Converter

[![GitHub](https://img.shields.io/github/stars/joris-vaneyghen/musx2mxl?style=social)](https://github.com/joris-vaneyghen/musx2mxl)

## About
This project is a private initiative aimed at musicians and composers who no longer have a valid Finale license and have no other alternative than the built-in Finale export function. This converter allows users to transform **Finale (.musx) music scores** into **MusicXML (.mxl) format**, making it possible to import them into various music notation software.

**Note:** This converter currently supports only **basic notations** and does not guarantee the exact preservation of bar positions, note placements, and other advanced notations. It is still a **work in progress**.


## Online File Converter
Check out the [online musx2xml converter](https://jorisvaneyghen-musx2mxl.hf.space/)


#### Run the Online File Converter local on your computer
```sh
docker run -it -p 7860:7860 --platform=linux/amd64 \
	registry.hf.space/jorisvaneyghen-musx2mxl:latest python app.py
```
After successful execution open [http://localhost:7860/](http://localhost:7860/) in your web browser  

For implementation details check [git](https://huggingface.co/spaces/jorisvaneyghen/musx2mxl/tree/main)


## Installation
To install the required package, use:
```sh
pip install musx2mxl
```

## Usage
### GUI:

```sh
musx2mxl-gui
```
### CMD line execution (batch)
You can use the converter via the command line:
```sh
musx2mxl [options] input_path
```

```
  input_path        A Finale file (*.musx) or a directory containing several Finale files.  
```

### Options:
```
  -h, --help        Show this help message and exit.
  --output_path     Path to the output .mxl file. Default value is the same as the input_path but with extension (*.mxl) (Is ignored if input_path is a directory).
  --keep            Keep the decoded Finale data (*.enigmaxml) and uncompressed MuscicXml (*.musicxml).
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

