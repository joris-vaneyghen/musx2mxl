from pathlib import Path

from setuptools import setup, find_packages

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read dependencies from requirements.txt
requirements_path = this_directory / "requirements.txt"
install_requires = requirements_path.read_text().splitlines() if requirements_path.exists() else []

setup(
    name="musx2mxl",  # Package name
    version="0.1.6",  # Version
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
