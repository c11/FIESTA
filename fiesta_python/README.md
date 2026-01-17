# FIESTA-Py: Forest Inventory Estimation and Analysis (Python)

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-GPL--3-green)

## Overview

**FIESTA-Py** is a Python implementation of the FIESTA (Forest Inventory ESTimation and Analysis) package, originally developed in R by the U.S. Department of Agriculture, Forest Service, Forest Inventory and Analysis (FIA) Program.

FIESTA-Py is a research estimation tool for analysts working with sample-based inventory data. It can generate FIA's traditional state-wide estimates while accommodating:

- Unique population boundaries
- Different evaluation time periods  
- Customized stratification schemes
- Non-standard variance equations
- Integration of multi-scale remotely-sensed data
- Other auxiliary information
- Interaction with other modeling and estimation tools

## Features

### Core Functions

- **Database tools (`db.*`)** - Functions for querying and extracting data from FIA's national database
- **Data tools (`dat.*`)** - Functions for summarizing and exploring FIA data
- **Spatial tools (`sp.*`)** - Functions for manipulating and summarizing spatial data

### Estimation Modules

- **Green-Book (`mod.gb.*`)** - Functions for FIA's standard Green-Book estimators
- **Photo-Based (`mod.pb.*`)** - Functions for supplementary photo-based estimators
- **Small Area (`mod.sa.*`)** - Functions for integration with available small area estimators (SAE)
- **Model-Assisted (`mod.ma.*`)** - Functions for integration with available Model-Assisted estimators

## Installation

### From source

```bash
git clone https://github.com/USDAForestService/FIESTA-Python.git
cd FIESTA-Python/fiesta_python
pip install -e .
```

### Using pip (when published)

```bash
pip install fiesta-py
```

## Quick Start

```python
import fiesta
from fiesta.dat import filter_data
from fiesta.sp import import_spatial
from fiesta.mod.gb import area_estimates

# Import spatial boundary
boundary = import_spatial("path/to/boundary.shp")

# Load FIA data
plots = fiesta.db.get_plots(states=["WY"], evalid="561301")

# Filter data
filtered_data = filter_data(plots, filter_expr="STATUSCD == 1")

# Generate area estimates
estimates = area_estimates(
    GBpopdat=population_data,
    landarea="FOREST",
    rowvar="FORTYPCD"
)

print(estimates['est'])
```

## Package Structure

```
fiesta/
├── __init__.py           # Main package initialization
├── db/                   # Database tools (DB*)
│   ├── __init__.py
│   ├── get_csv.py
│   ├── get_plots.py
│   ├── get_sqlite.py
│   └── ...
├── dat/                  # Data manipulation tools (dat*)
│   ├── __init__.py
│   ├── filter.py
│   ├── freq.py
│   ├── pivot.py
│   └── ...
├── sp/                   # Spatial tools (sp*)
│   ├── __init__.py
│   ├── import_spatial.py
│   ├── extract_raster.py
│   ├── clip_poly.py
│   └── ...
├── mod/                  # Estimation modules
│   ├── __init__.py
│   ├── gb/              # Green-Book estimators
│   ├── pb/              # Photo-based estimators
│   ├── sa/              # Small area estimators
│   └── ma/              # Model-assisted estimators
└── utils/               # Utility functions
    ├── __init__.py
    ├── checks.py
    └── helpers.py
```

## Dependencies

- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **geopandas**: Geographic data handling
- **shapely**: Geometric operations
- **rasterio**: Raster data I/O and processing
- **sqlalchemy**: Database connectivity
- **matplotlib**: Plotting and visualization
- **scipy**: Statistical functions
- **scikit-learn**: Machine learning utilities

## R to Python Mapping

| R Package | Python Package | Purpose |
|-----------|----------------|---------|
| data.table | pandas | Data manipulation |
| sf | geopandas | Spatial vector data |
| terra/raster | rasterio | Spatial raster data |
| DBI/RSQLite | sqlalchemy | Database connections |
| ggplot2 | matplotlib/seaborn | Visualization |

## Documentation

Full documentation is available at [https://fiesta-py.readthedocs.io](https://fiesta-py.readthedocs.io) (when published).

For the original R package documentation, see: [https://usdaforestservice.github.io/FIESTA/](https://usdaforestservice.github.io/FIESTA/)

## Contributing

Contributions are welcome! Please read our contributing guidelines and code of conduct.

## License

GPL-3 License - See LICENSE file for details.

## Citation

If you use FIESTA-Py in your research, please cite:

```
Frescino, T.S., Moisen, G.G., Patterson, P.L., Toney, C., White, G., Yamamoto, J. (2024).
FIESTA-Py: Forest Inventory Estimation and Analysis Python Package.
USDA Forest Service, Rocky Mountain Research Station.
```

## Contact

- Issues: [GitHub Issues](https://github.com/USDAForestService/FIESTA-Python/issues)
- Email: fiesta-dev@usda.gov

## Acknowledgments

This Python implementation is based on the original FIESTA R package developed by the USDA Forest Service, Rocky Mountain Research Station.
