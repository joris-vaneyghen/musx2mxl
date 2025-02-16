from pathlib import Path
import re
from setuptools import setup, find_packages

# Read the version from the package
version_path = Path(__file__).parent / "musx2mxl" / "__init__.py"
version_match = re.search(r'__version__ = ["\']([^"\']+)["\']', version_path.read_text())
if not version_match:
    raise RuntimeError("Unable to find version string in musx2mxl/__init__.py")
version = version_match.group(1)

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read dependencies from requirements.txt
requirements_path = this_directory / "requirements.txt"
install_requires = requirements_path.read_text().splitlines() if requirements_path.exists() else []

setup(
    name="musx2mxl",  # Package name
    version=version,  # Dynamically read version
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),  # Automatically find package directories
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "musx2mxl=musx2mxl.musx2mxl:main",  # Creates a CLI command
            "musx2mxl-gui=musx2mxl.musx2mxl_gui:main",  # Creates a CLI command
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.6",
)
