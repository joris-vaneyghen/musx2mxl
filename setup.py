from setuptools import setup, find_packages

setup(
    name="musx2mxl",  # Package name
    version="0.1.0",  # Version
    packages=find_packages(),  # Automatically find package directories
    install_requires=[],  # Dependencies (e.g., install_requires=["numpy"])
    entry_points={
        "console_scripts": [
            "musx2mxl=musx2mxl.musx2mxl:main",  # Creates a CLI command
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.6",
)