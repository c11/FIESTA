"""
FIESTA-Py: Forest Inventory Estimation and Analysis
====================================================

FIESTA-Py is a research estimation tool for analysts working with sample-based 
inventory data from the U.S. Department of Agriculture, Forest Service, 
Forest Inventory and Analysis (FIA) Program.

Main modules:
- db: Database tools for querying and extracting FIA data
- dat: Data manipulation and analysis tools
- sp: Spatial data processing tools
- mod: Estimation modules (Green-Book, Photo-Based, Small Area, Model-Assisted)

Example:
    >>> import fiesta
    >>> from fiesta.dat import filter_data
    >>> from fiesta.mod.gb import area_estimates
"""

__version__ = "0.1.0"
__author__ = "FIESTA Development Team"
__license__ = "GPL-3"

# Import main submodules
from fiesta import db
from fiesta import dat
from fiesta import sp
from fiesta import mod
from fiesta import utils

# Define public API
__all__ = [
    "db",
    "dat", 
    "sp",
    "mod",
    "utils",
    "__version__",
]
