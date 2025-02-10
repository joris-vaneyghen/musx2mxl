# Finale to MusicXML Converter

[![GitHub](https://img.shields.io/github/stars/joris-vaneyghen/musx2mxl?style=social)](https://github.com/joris-vaneyghen/musx2mxl)

## About
This project is a private initiative aimed at musicians and composers who no longer have a valid Finale license and have no other alternative than the built-in Finale export function. This converter allows users to transform **Finale (.musx) music scores** into **MusicXML (.mxl) format**, making it possible to import them into various music notation software.

**Note:** This converter currently supports only **basic notations** and does not guarantee the exact preservation of bar positions, note placements, and other advanced notations. It is still a **work in progress**.


## Online File Converter
Check out the [online musx2xml converter](https://jorisvaneyghen-musx2mxl.hf.space/)

## Installation
To install the required package, use:
```sh
pip install musx2mxl
```

## Usage
You can use the converter via the command line:
```sh
musx2mxl [options] input_file
```

### Options:
```
  -h, --help        show this help message and exit
  --output_path     Path to the output .mxl file.
  --keep            Keep decoded enigmaxml and uncompressed musicxml
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

