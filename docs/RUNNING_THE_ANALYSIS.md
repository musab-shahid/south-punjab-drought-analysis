# Running the analysis

This guide describes the actual configuration and workflow of `notebooks/drought_study.ipynb`. It is not a claim of clean-environment reproduction.

## Environment and services

- Google Colab Python environment
- Google Earth Engine account and an authorized Cloud project (set in `GEE_PROJECT`)
- Google Drive mounted in Colab (the notebook sets `MOUNT_DRIVE = True`)
- Python packages required by the notebook, including `earthengine-api`, `numpy`, `pandas`, and additional analysis/plotting packages used in subsequent sections. Package versions are not pinned.
- Inputs and exported CSVs from the [research archive](https://drive.google.com/drive/folders/1EFKdIpvvfyv1FfrVnsm2TWeDFcsamxs-?usp=sharing)

## Folder layout

The notebook expects `PROJECT_DIR = "/content/drive/MyDrive/AiRCAS_drought/"` and uses:

```text
AiRCAS_drought/
├── gee_exports/       # Monthly district CSVs and canal exposure exports
├── source_data/        # Wheat-yield panel and required source files
├── analysis_outputs/   # Analysis tables, models, and plots
│   └── figures/
└── osm_canals_geojson/ # Canal lines, if needed for fresh exports
```

The `CANAL_GEOJSON_PATH` variable in the original notebook points to `osm canals geojson/south_punjab_osm_canals.geojson`, while the archived Drive folder is named `osm_canals_geojson`. The notebook also searches alternative locations. For a fresh run, **verify or change this path** to match your mounted Drive folder.

## Two run modes

1. **Export mode:** Set `RUN_GEE_EXPORTS = True` and `RUN_ANALYSIS = False`. Set `GEE_PROJECT`, authenticate Earth Engine, mount Drive, and start the export tasks. Wait for all tasks to complete in Earth Engine before proceeding.
2. **Analysis mode:** Set `RUN_GEE_EXPORTS = False`, `RUN_ANALYSIS = True`, and `RUN_PLOTS = True`. Place the finished exports and required wheat/canal inputs in the expected folders. The committed notebook is configured in this mode.

The original code uses the official wheat-panel filename `south_punjab_wheat_official_2000_2024.csv`; check it exists in `source_data/` before expecting the published regression outputs.

## Important caveats

- The notebook uses a **single code cell** with multiple stages; users should inspect flags and paths before running it.
- Earth Engine exports are asynchronous and dependent on account permissions and source availability.
- Reproducing tables and figures requires the correct inputs, data vintages, and software environment.
- Do not treat the soil-water variable as direct satellite measurements: it is **ERA5-Land reanalysis**.
- The report summarizes results; published GitHub notebook and figures have not been independently rerun in a clean environment.

For canonical scientific definitions and caveats, consult the [final research report](https://docs.google.com/document/d/1OdzCHDSjB3KY8uIO5WPtR0P9SAUqHI1S/edit).
