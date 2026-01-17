# FIESTA Estimation Modules - Complete Reference

## Overview

FIESTA (Forest Inventory ESTimation and Analysis) provides multiple estimation methodologies for forest inventory data. This document provides a complete reference for all estimation modules.

## Module Structure

```
fiesta/mod/
├── gb/          # Green-Book estimation
│   ├── area.py       # Area estimation
│   ├── tree.py       # Tree/volume estimation
│   ├── ratio.py      # Ratio estimation
│   └── population.py # Population data preparation
├── pb/          # Photo-Based estimation
├── ma/          # Model-Assisted estimation
└── sa/          # Small Area estimation
```

## Green-Book (GB) Estimation

Based on Scott et al. (2005) - the "Green Book" for FIA estimation.

### 1. Area Estimation (`gb_area_estimates`)

**Purpose**: Estimate forest area by domain (e.g., forest type, ownership).

**Method**: Non-ratio estimator using condition proportions and expansion factors.

**Parameters**:
- `tree_df`: Tree data
- `cond_df`: Condition data
- `pltassgn_df`: Plot assignment with strata
- `rowvar`: Row domain variable (optional)
- `colvar`: Column domain variable (optional)
- `landarea`: Land area filter ('ALL', 'FOREST', 'TIMBERLAND')
- `confidence_level`: Confidence level for PSE (default 0.68)

**Returns**:
- `est`: DataFrame with estimates and variance
- `pse`: DataFrame with percent sampling error
- `raw`: Dictionary with raw processing data

**Example**:
```python
from fiesta.mod.gb import gb_area_estimates

result = gb_area_estimates(
    tree_df=trees,
    cond_df=conditions,
    pltassgn_df=plots,
    rowvar='FORTYPCD',
    landarea='FOREST'
)

print(result['est'])  # Estimates by forest type
print(result['pse'])  # Percent sampling errors
```

### 2. Tree/Volume Estimation (`gb_tree_estimates`)

**Purpose**: Estimate tree attributes (volume, biomass, carbon) per acre.

**Method**: Non-ratio estimator with TPA (trees per acre) adjustments.

**Parameters**:
- `tree_df`: Tree data with estimate variable
- `cond_df`: Condition data with proportions
- `pltassgn_df`: Plot assignment data
- `estvarn`: Estimate variable name (e.g., 'VOLCFNET', 'CARBON_AG')
- `estvarn_filter`: Filter expression for estimate variable (optional)
- `rowvar`: Row domain variable (optional)
- `colvar`: Column domain variable (optional)
- `tpa_var`: Trees per acre variable (default 'TPA_UNADJ')
- `landarea`: Land area filter
- `confidence_level`: Confidence level for PSE

**Key Features**:
- Applies TPA adjustments for per-acre estimates
- Handles derived variables (multiplication/division)
- Supports woodland vs. timberland filtering
- Stratified variance estimation

**Example**:
```python
from fiesta.mod.gb import gb_tree_estimates

# Volume per acre by species
result = gb_tree_estimates(
    tree_df=trees,
    cond_df=conditions,
    pltassgn_df=plots,
    estvarn='VOLCFNET',
    rowvar='SPCD',
    estvarn_filter='DIA >= 5.0'
)

# Carbon per acre by forest type
result = gb_tree_estimates(
    tree_df=trees,
    cond_df=conditions,
    pltassgn_df=plots,
    estvarn='CARBON_AG',
    rowvar='FORTYPCD'
)
```

### 3. Ratio Estimation (`gb_ratio_estimates`)

**Purpose**: Generate ratio-of-means estimates (e.g., volume per tree, volume per acre).

**Method**: Ratio-of-means estimator with delta method for variance.

**Parameters**:
- `tree_df`: Tree data
- `cond_df`: Condition data
- `pltassgn_df`: Plot assignment data
- `estvarn`: Numerator variable
- `estvard`: Denominator variable
- `ratio_type`: 'PERACRE' or 'PERTREE'
- `estvarn_filter`: Numerator filter (optional)
- `estvard_filter`: Denominator filter (optional)
- `rowvar`: Row domain variable (optional)
- `tpa_var`: Trees per acre variable

**Example**:
```python
from fiesta.mod.gb import gb_ratio_estimates, calculate_per_acre_ratio

# Volume per acre by species
result = calculate_per_acre_ratio(
    tree_df=trees,
    cond_df=conditions,
    pltassgn_df=plots,
    numerator_var='VOLCFNET',
    rowvar='SPCD'
)

# Average DBH per tree by forest type
result = gb_ratio_estimates(
    tree_df=trees,
    cond_df=conditions,
    pltassgn_df=plots,
    estvarn='DIA',
    estvard='TPA_UNADJ',
    ratio_type='PERTREE',
    rowvar='FORTYPCD'
)
```

### 4. Population Preparation (`gb_population`)

**Purpose**: Prepare population data with adjustment factors for GB estimation.

**Method**: Calculate plot-level or stratum-level adjustment factors and weights.

**Parameters**:
- `cond_df`: Condition data
- `pltassgn_df`: Plot assignment data
- `unitarea_df`: Area by estimation unit (optional)
- `adj_type`: 'PLOT' or 'STRATUM' level adjustments
- `popType`: Population type ('ALL', 'CURR', 'VOL', 'LULC')

**Key Features**:
- Calculates adjustment factors (ADJUSTSQR)
- Computes strata weights
- Handles multiple population types
- Supports tree and seedling data

**Example**:
```python
from fiesta.mod.gb import gb_population

pop_data = gb_population(
    cond_df=conditions,
    pltassgn_df=plots,
    unitarea_df=unit_areas,
    adj_type='STRATUM'
)

# Use in estimation
result = gb_area_estimates(
    tree_df=trees,
    cond_df=pop_data['cond'],
    pltassgn_df=pop_data['pltassgn']
)
```

## Photo-Based (PB) Estimation

Based on Patterson (2012) - photo-based inventory estimators.

### Photo-Based Estimates (`pb_estimates`)

**Purpose**: Generate percent cover or area estimates from photo interpretation.

**Method**: Simple random sampling or stratified estimators for point-based data.

**Parameters**:
- `pnt_df`: Point data with photo interpretation
- `plt_df`: Plot assignment data
- `unitarea_df`: Area by estimation unit
- `tabtype`: 'PCT' for percent or 'AREA' for area
- `rowvar`: Domain variable (e.g., land cover class)
- `colvar`: Second domain variable (optional)
- `nonsamp_pntfilter`: Filter for nonsampled points (e.g., clouds)
- `pntfilter`: Global point filter
- `unitvar`: Estimation unit variable (default 'ESTN_UNIT')

**Example**:
```python
from fiesta.mod.pb import pb_estimates

# Percent cover by land cover class
result = pb_estimates(
    pnt_df=points,
    plt_df=plots,
    unitarea_df=unit_areas,
    tabtype='PCT',
    rowvar='cover_1',
    nonsamp_pntfilter='cover_1 != 999'
)

# Area estimates by county
result = pb_estimates(
    pnt_df=points,
    plt_df=plots,
    unitarea_df=unit_areas,
    tabtype='AREA',
    rowvar='cover_1',
    unitvar='COUNTY'
)
```

### Photo-Based Ratio (`pb_ratio_estimates`)

**Purpose**: Calculate ratio estimates for photo-based data.

**Example**:
```python
from fiesta.mod.pb import pb_ratio_estimates

result = pb_ratio_estimates(
    pnt_df=points,
    plt_df=plots,
    unitarea_df=unit_areas,
    numerator='forest_cover',
    denominator='total_cover'
)
```

## Model-Assisted (MA) Estimation

Integrates auxiliary spatial data (e.g., remote sensing) to improve estimates.

### Model-Assisted Area (`ma_area_estimates`)

**Purpose**: Improve area estimates using auxiliary data.

**Methods**:
- `POSTSTRAT`: Post-stratification using auxiliary data
- `REGRESSION`: Regression estimator with auxiliary variables

**Parameters**:
- `tree_df`: Tree data
- `cond_df`: Condition data
- `pltassgn_df`: Plot assignment data
- `auxiliary_df`: Auxiliary spatial data
- `modeltype`: 'POSTSTRAT' or 'REGRESSION'
- `rowvar`: Domain variable (optional)

**Example**:
```python
from fiesta.mod.ma import ma_area_estimates

# Post-stratified estimates
result = ma_area_estimates(
    tree_df=trees,
    cond_df=conditions,
    pltassgn_df=plots,
    auxiliary_df=landcover_data,
    modeltype='POSTSTRAT',
    rowvar='FORTYPCD'
)

# Regression estimates with NDVI
result = ma_area_estimates(
    tree_df=trees,
    cond_df=conditions,
    pltassgn_df=plots,
    auxiliary_df=ndvi_data,
    modeltype='REGRESSION'
)
```

## Small Area (SA) Estimation

Provides reliable estimates for small domains with limited samples.

### Small Area Estimates (`sa_area_estimates`)

**Purpose**: Generate estimates for small domains (e.g., counties, sub-regions).

**Methods**:
- `DIRECT`: Use only sample from small domain
- `SYNTHETIC`: Use larger area rate applied to small domain
- `COMPOSITE`: Combine direct and synthetic estimates

**Parameters**:
- `tree_df`: Tree data
- `cond_df`: Condition data
- `pltassgn_df`: Plot assignment data
- `smalldomain`: Small domain variable
- `auxiliary_df`: Auxiliary data (for SYNTHETIC/COMPOSITE)
- `method`: 'DIRECT', 'SYNTHETIC', or 'COMPOSITE'

**Example**:
```python
from fiesta.mod.sa import sa_area_estimates

# Direct estimates by county
result = sa_area_estimates(
    tree_df=trees,
    cond_df=conditions,
    pltassgn_df=plots,
    smalldomain='COUNTYCD',
    method='DIRECT'
)

# Synthetic estimates using state-level rates
result = sa_area_estimates(
    tree_df=trees,
    cond_df=conditions,
    pltassgn_df=plots,
    smalldomain='COUNTYCD',
    auxiliary_df=county_areas,
    method='SYNTHETIC'
)

# Composite (weighted) estimates
result = sa_area_estimates(
    tree_df=trees,
    cond_df=conditions,
    pltassgn_df=plots,
    smalldomain='COUNTYCD',
    auxiliary_df=county_areas,
    method='COMPOSITE'
)
```

## Common Output Structure

All estimation functions return a dictionary with:

```python
{
    'est': DataFrame,      # Estimates with variance
    'pse': DataFrame,      # Percent sampling errors
    'raw': dict           # Raw processing data
}
```

### Estimates DataFrame (`est`)
- Domain variables (if specified)
- `ESTIMATE` or `EST`: Point estimate
- `VARIANCE`: Variance of estimate

### PSE DataFrame (`pse`)
- Domain variables (if specified)
- `PSE`: Percent sampling error

### Raw Data (`raw`)
- Processing details
- Sample sizes
- Intermediate calculations

## Data Requirements

### Required Columns

**Tree Data**:
- `PLT_CN`: Plot identifier
- `TPA_UNADJ`: Trees per acre (unadjusted)
- Estimate variables (e.g., `VOLCFNET`, `DIA`, `CARBON_AG`)

**Condition Data**:
- `PLT_CN`: Plot identifier
- `CONDID`: Condition identifier
- `CONDPROP_UNADJ`: Condition proportion (unadjusted)
- `COND_STATUS_CD`: Condition status

**Plot Assignment Data**:
- `CN` or `PLT_CN`: Plot identifier
- `STRATUMCD`: Stratum code (for stratified estimation)
- Domain variables (e.g., `COUNTYCD`, `STATECD`)

**Unit Area Data** (for area estimation):
- Unit variable (e.g., `ESTN_UNIT`, `COUNTYCD`)
- `AREA`: Area of estimation unit

## Variance Estimation

All modules use design-based variance estimators:

1. **Simple Random Sampling**: $Var(\bar{y}) = \frac{s^2}{n}$

2. **Stratified Sampling**: $Var(\bar{y}_{st}) = \sum_{h} w_h^2 \frac{s_h^2}{n_h}$

3. **Ratio Estimator** (delta method):
   $$Var(R) = \frac{1}{\bar{x}^2}[Var(\bar{y}) + R^2 Var(\bar{x}) - 2R Cov(\bar{y}, \bar{x})]$$

4. **Post-Stratified**: Similar to stratified but weights from population

## Percent Sampling Error (PSE)

PSE measures relative precision:

$$PSE = \frac{t_{\alpha/2} \times SE}{Estimate} \times 100$$

Where:
- $t_{\alpha/2}$: t-statistic for confidence level
- $SE = \sqrt{Variance}$: Standard error

Default confidence level: 68% (≈1 standard error)

## Best Practices

1. **Choose Appropriate Estimator**:
   - Use GB for traditional FIA estimation
   - Use PB for photo-based inventories
   - Use MA when auxiliary data available
   - Use SA for small domains with sparse data

2. **Check Sample Sizes**:
   - Minimum 3-5 plots per domain for reliable estimates
   - Consider combining small domains
   - Use SA methods for domains with <10 plots

3. **Apply Appropriate Filters**:
   - Filter nonsampled conditions
   - Apply land area filters consistently
   - Document all filters used

4. **Validate Results**:
   - Check PSE values (target <50%)
   - Verify totals sum correctly
   - Compare with known values when possible

5. **Stratification**:
   - Use stratification when available
   - Ensure strata weights sum to 1
   - Check for empty strata

## References

1. Scott, C.T., Bechtold, W.A., Reams, G.A., Smith, W.D., Westfall, J.A., Hansen, M.H., and Moisen, G.G. 2005. Sample-based estimators used by the Forest Inventory and Analysis national information management system. Gen. Tech. Rep. SRS-80. Asheville, NC: USDA Forest Service, Southern Research Station. 43 p.

2. Patterson, P.L. 2012. Photo-based estimators for the Nevada photo-based inventory. Res. Pap. RMRS-RP-92. Fort Collins, CO: USDA Forest Service, Rocky Mountain Research Station. 14 p.

3. Bechtold, W.A. and Patterson, P.L., eds. 2005. The enhanced forest inventory and analysis program - national sampling design and estimation procedures. Gen. Tech. Rep. SRS-80. Asheville, NC: USDA Forest Service, Southern Research Station. 85 p.

## Support

For questions or issues:
- GitHub Issues: [your-repo-url]
- FIESTA R package: https://github.com/USDAForestService/FIESTA
- FIA Data: https://www.fia.fs.fed.us/

---

*This implementation is based on the USDA Forest Service FIESTA R package.*
