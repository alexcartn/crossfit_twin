"""
Setup script for CrossFit Digital Twin library.
This ensures the package is properly installed in Streamlit Cloud.
"""

from setuptools import setup, find_packages

setup(
    name="crossfit-twin",
    version="0.1.0",
    description="A Python library for simulating CrossFit athlete performance",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.20.0",
        "pandas>=1.3.0",
    ],
    python_requires=">=3.8",
)