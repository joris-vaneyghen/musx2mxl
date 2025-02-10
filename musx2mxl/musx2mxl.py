import argparse
import gzip
import os
import traceback
import zipfile
from io import BytesIO

from musx2mxl import converter

# Constants for the MUSX PRNG-based stream cipher
CIPHER_INITIAL_STATE = 0x28006D45
CIPHER_MULTIPLIER = 0x41C64E6D
CIPHER_INCREMENT = 0x3039
CIPHER_RESET_INTERVAL = 0x20000

def decrypt(buffer):
    """
    Encrypts/decrypts a buffer in place using a custom PRNG-based stream cipher.

    Args:
        buffer (bytearray): The data to be encrypted/decrypted.
    """
    state = CIPHER_INITIAL_STATE

    for i in range(len(buffer)):
        if i % CIPHER_RESET_INTERVAL == 0:
            state = CIPHER_INITIAL_STATE

        state = (state * CIPHER_MULTIPLIER + CIPHER_INCREMENT) & 0xFFFFFFFF
        upper = state >> 16
        pseudo_random_byte = (upper + upper // 255) & 0xFF
        buffer[i] ^= pseudo_random_byte


# def extract_zip(file_path):
#     """
#     Extracts the contents of a zip file to a directory with the same base name.
#
#     Args:
#         file_path (str): Path to the zip file.
#
#     Returns:
#         str: Path to the extracted directory.
#     """
#     output_dir = os.path.splitext(file_path)[0]
#     with zipfile.ZipFile(file_path, 'r') as zip_ref:
#         zip_ref.extractall(output_dir)
#     return output_dir

def read_file_from_zip(file_path, target_file):
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        if target_file in zip_ref.namelist():
            with zip_ref.open(target_file, 'r') as file:
                return bytearray(file.read())  # Returns the binary content of the file
        else:
            raise FileNotFoundError(f"{target_file} not found in the archive.")


# def decompress_data(data, output_file):
#     """
#     Decompresses gzip data and writes the decompressed data to a file.
#
#     Args:
#         data (bytearray): Gzip-compressed data.
#         output_file (str): Path to the output file.
#     """
#     # Decompress the gzip data directly in memory
#     decompressed_data = gzip.decompress(data)
#
#     # Write the decompressed data to the output file
#     with open(output_file, 'wb') as f:
#         f.write(decompressed_data)

def decompress_data(data):
    """
    Decompresses gzip data, writes the decompressed data to a binary buffer,
    and parses the buffer as an XML document.

    Args:
        data (bytearray): Gzip-compressed data.

    Returns:
        bytearray.
    """
    # Decompress the gzip data directly in memory
    return gzip.decompress(data)


def read_file(file_path):
    """
    Reads the contents of a file and returns it as a bytearray.

    Args:
        file_path (str): Path to the file.

    Returns:
        bytearray: File contents.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "rb") as file:
        return bytearray(file.read())


def write_file(file_path, data):
    """
    Writes data to a file.

    Args:
        file_path (str): Path to the file.
        data (bytes or bytearray): Data to write.
    """
    with open(file_path, "wb") as file:
        file.write(data)


def save_as_mxl(data, output_path, musicxml_filename="score.musicxml"):
    """
    Save an ElementTree XML object as a compressed MXL file directly to a zip archive.

    Args:
        data: Data (score.musicxml) to compress.
        output_path: Path to save the .mxl file.
        musicxml_filename: Name of the main MusicXML file within the MXL package.
    """

    data.seek(0)

    # Create the container.xml content
    container_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<container>
  <rootfiles>
    <rootfile full-path="{musicxml_filename}" media-type="application/vnd.recordare.musicxml+xml"/>
  </rootfiles>
</container>
"""
    container_data = container_content.encode("utf-8")
    # Mimetype content
    mimetype_content = b"application/vnd.recordare.musicxml"

    # Write all data directly into a zip archive
    with zipfile.ZipFile(output_path, "w") as mxl_zip:
        # Add the mimetype file (must be uncompressed and first in the archive)
        mxl_zip.writestr("mimetype", mimetype_content, compress_type=zipfile.ZIP_STORED)
        # Add the MusicXML content
        mxl_zip.writestr(musicxml_filename, data.getvalue(), compress_type=zipfile.ZIP_DEFLATED)
        # Add the container.xml
        mxl_zip.writestr("META-INF/container.xml", container_data, compress_type=zipfile.ZIP_DEFLATED)

def convert_file(input_path, output_path, keep = False):
    data = read_file_from_zip(input_path, 'score.dat')
    metadata = read_file_from_zip(input_path, 'NotationMetadata.xml')
    decrypt(data)
    data = gzip.decompress(data)
    if keep:
        with open(output_path.replace(".mxl", ".enigmaxml"), "wb") as file:
            file.write(data)
    input_stream = BytesIO(data)
    metadata_stream = BytesIO(metadata)
    output_stream = BytesIO()
    converter.convert_from_stream(input_stream, metadata_stream, output_stream)
    if keep:
        with open(output_path.replace(".mxl", ".musicxml"), "wb") as file:
            output_stream.seek(0)
            file.write(output_stream.getvalue())
    save_as_mxl(output_stream, output_path)


def main():
    """
    Main function to parse arguments and process the musx file.
    """
    parser = argparse.ArgumentParser(description="Convert a Finale .musx file to MusicXml .mxl file.")
    parser.add_argument("musx_file", help="Path to the Finale .musx file.")
    parser.add_argument("--output_path", default=None, required=False, help="Path to the output .mxl file.")
    parser.add_argument("--keep",  default=False, required=False, help="Keep decoded enigmaxml and uncompressed musicxml")
    args = parser.parse_args()
    input_path = args.musx_file
    assert input_path.endswith(".musx")
    output_path = args.output_path
    if output_path:
        assert output_path.endswith(".mxl")
    else:
        output_path = input_path.replace(".musx", ".mxl")
    keep = args.keep

    try:
        convert_file(input_path, output_path, keep)
        print("Processing complete!")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
