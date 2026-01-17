"""Setup configuration for FIESTA Python package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fiesta-py",
    version="0.1.0",
    author="FIESTA Development Team",
    author_email="fiesta-dev@usda.gov",
    description="Forest Inventory Estimation and Analysis - Python Implementation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/USDAForestService/FIESTA-Python",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: GIS",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pandas>=1.5.0",
        "numpy>=1.21.0",
        "geopandas>=0.12.0",
        "shapely>=2.0.0",
        "pyproj>=3.3.0",
        "rasterio>=1.3.0",
        "fiona>=1.9.0",
        "sqlalchemy>=2.0.0",
        "matplotlib>=3.5.0",
        "scipy>=1.9.0",
        "scikit-learn>=1.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
            "sphinx>=4.5.0",
        ],
    },
    include_package_data=True,
    package_data={
        "fiesta": ["data/*.csv", "data/*.json"],
    },
)
