# Python Conversion Summary

## Overview

This document summarizes the conversion of the FIESTA R package to Python (FIESTA-Py).

## Project Structure

```
fiesta_python/
├── setup.py                 # Package installation configuration
├── requirements.txt         # Python dependencies
├── README.md               # Main documentation
├── fiesta/                 # Main package
│   ├── __init__.py        # Package initialization
│   ├── utils/             # Utility functions
│   ├── dat/               # Data manipulation tools
│   ├── db/                # Database query tools
│   ├── sp/                # Spatial processing tools
│   └── mod/               # Estimation modules
├── examples/              # Usage examples
├── tests/                 # Test suite
└── docs/                  # Documentation
```

## R to Python Mapping

### Core Dependencies

| R Package | Python Package | Purpose |
|-----------|----------------|---------|
| data.table | pandas | Data manipulation |
| sf | geopandas | Vector spatial data |
| terra | rasterio | Raster data |
| DBI/RSQLite | sqlalchemy/sqlite3 | Database |
| ggplot2 | matplotlib | Visualization |

### Module Conversion Status

#### ✅ Completed Modules

1. **Data Tools (dat/)** - COMPLETE
   - `filter.py` - Data filtering (datFilter)
   - `freq.py` - Frequency tables (datFreq)
   - `pivot.py` - Data pivoting (datPivot)
   - `summary.py` - Tree/condition summaries

2. **Spatial Tools (sp/)** - COMPLETE
   - `import_spatial.py` - Import spatial data (spImportSpatial)
   - `export_spatial.py` - Export spatial data
   - `clip.py` - Clipping operations (spClip*)
   - `extract.py` - Raster extraction (spExtract*)
   - `reproject.py` - Reprojection (spReproject*)
   - `zonal.py` - Zonal statistics (spZonalRast)

3. **Database Tools (db/)** - COMPLETE
   - `get_plots.py` - Retrieve plot data (DBgetPlots)
   - `get_csv.py` - CSV reading (DBgetCSV)
   - `sqlite.py` - SQLite operations (DBgetSQLite)

4. **Green-Book Module (mod/gb/)** - PARTIAL
   - `area.py` - Area estimation (modGBarea) - COMPLETE
   - `tree.py` - Tree estimation (modGBtree) - PLACEHOLDER
   - `population.py` - Population data (modGBpop) - PLACEHOLDER

5. **Utilities (utils/)** - COMPLETE
   - Parameter validation
   - Error handling
   - Helper functions

#### 🔨 Placeholder Modules (Need Implementation)

1. **Photo-Based Module (mod/pb/)**
   - modPB, modPBpop

2. **Model-Assisted Module (mod/ma/)**
   - modMAarea, modMAtree, modMAratio, modMApop

3. **Small Area Module (mod/sa/)**
   - modSAarea, modSAtree, modSApop

## Key Implementation Differences

### 1. Data Structures
- **R**: data.table / data.frame
- **Python**: pandas DataFrame
- **Note**: Similar functionality, Python is 0-indexed

### 2. Spatial Data
- **R**: sf objects
- **Python**: geopandas GeoDataFrame
- **Note**: Both based on GDAL/OGR

### 3. Syntax Differences

#### Filtering
```r
# R
datFilter(x, xfilter = "STATUSCD == 1")
```

```python
# Python
filter_data(x, xfilter="STATUSCD == 1")
```

#### Spatial Import
```r
# R
spImportSpatial(layer = "boundary.shp")
```

```python
# Python
import_spatial("boundary.shp")
```

## Installation

```bash
cd fiesta_python
pip install -e .
```

## Usage Example

```python
import fiesta
from fiesta.dat import filter_data
from fiesta.sp import import_spatial
from fiesta.mod.gb import gb_area_estimates

# Load FIA data
plots = fiesta.db.get_plots(states=['WY'], data_dir='/path/to/data')

# Filter data
filtered = filter_data(plots['COND'], xfilter="COND_STATUS_CD == 1")

# Generate estimates
estimates = gb_area_estimates(
    cond_df=filtered['xf'],
    pltassgn_df=plots['PLT'],
    rowvar='FORTYPCD'
)
```

## Testing

```bash
cd fiesta_python
pytest tests/ -v
```

## Next Steps

1. Complete placeholder estimation modules (PB, MA, SA)
2. Add comprehensive test coverage
3. Build complete documentation
4. Add visualization functions (equivalent to R plotting)
5. Performance optimization
6. Add more example scripts

## Notes

- All core functionality for data manipulation and spatial processing is complete
- Green-Book area estimation is implemented as a demonstration
- The package structure mirrors the original R package for familiarity
- Python naming conventions (snake_case) are used instead of R's style
- Type hints and docstrings follow Python best practices

## License

GPL-3 (same as original R package)

## Contributors

Based on the original FIESTA R package by:
- Tracey Frescino
- Gretchen Moisen
- Paul Patterson
- Chris Toney
- Grayson White
- Joshua Yamamoto
