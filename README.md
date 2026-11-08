# Drought Event Analysis in South Punjab, Pakistan

*Multi-Sensor Remote Sensing of Precipitation, Soil Moisture, Vegetation and Thermal Cascades, and Exploratory Implications for Wheat Yield*
**Reader guide:** [Project structure and report status](docs/PROJECT_GUIDE.md) · [Public portfolio](https://musab-shahid-earth-observation.brinycourt4.chatgpt.site/)


**CHIRPS · ERA5-Land · MODIS · Google Earth Engine · Python · Drought-event statistics**

Independent, multi-sensor study of precipitation and soil-moisture drought events, vegetation/thermal responses and exploratory agricultural implications across **11 districts** of South Punjab.

**Researcher:** Musab Shahid  
**Research context:** Independent September 2026 application assignment for Dr. Chaolei Zheng, Aerospace Information Research Institute (AIRCAS), Chinese Academy of Sciences. **Not** a claim of institutional appointment, employment or endorsement.

> **Interpretation:** This is observational research. Temporal correlations are not proof of a causal drought cascade; proximity to mapped canals does not measure actual irrigation delivery; ERA5-Land soil water is model-based reanalysis.

## Explore the project

| Start here | What it contains |
| --- | --- |
| [Research figures](figures/) | Event timelines, Multan time series, lag-association heatmap, canal proximity and Terra–Aqua comparison |
| [Original research notebook](notebooks/drought_study.ipynb) | Published source notebook with Earth Engine exports and downstream analysis |
| [Notebook execution guide](docs/RUNNING_THE_ANALYSIS.md) | Two-stage GEE-export and Python-analysis workflow, account paths and caveats |
| [Final research report (Drive)](https://docs.google.com/document/d/1OdzCHDSjB3KY8uIO5WPtR0P9SAUqHI1S/edit) | Full methodological narrative and reported findings |
| [Research archive](https://drive.google.com/drive/folders/1EFKdIpvvfyv1FfrVnsm2TWeDFcsamxs-) | Original input files and supporting documents |
| [Analysis outputs (Drive)](https://drive.google.com/drive/folders/1QYWY2lwOiA_Gc5-DgkmRpD3U6hsRLaO-) | Outputs needed to check the published report |
| [Publication limitations and checklist](docs/PUBLISHING_CHECKLIST.md) | Outstanding independent replication and source-data checks |

## Research questions and study area

Across **Multan, Khanewal, Vehari, Lodhran, Bahawalpur, Bahawalnagar, Rahim Yar Khan, Muzaffargarh, Layyah, Dera Ghazi Khan and Rajanpur**, how do precipitation and modeled soil-moisture drought events differ? How do vegetation, evapotranspiration and surface-temperature anomalies co-vary, and what exploratory relationships appear with wheat yield and mapped canal proximity?

## Data sources and approach

| Environmental variable | Source | Analysis |
| --- | --- | --- |
| Precipitation | **CHIRPS v3** | SPI-1 / SPI-3 drought monitoring |
| Soil moisture, 0–100 cm | **ERA5-Land** | Reanalysis soil-water anomalies and events |
| Land-surface temperature | **MODIS Terra/Aqua** | Thermal anomalies, sensor consistency |
| Vegetation / evapotranspiration | **MODIS NDVI / MOD16A2GF ET** | Vegetation and moisture-response associations |
| Cropland / canal locations | **ESA WorldCover 2021 / OpenStreetMap** | Static mapped-canal proximity; sensitivity buffers |
| District wheat yields | Official agricultural series, with documented gap filling | Exploratory fixed-effect regressions |

**Workflow:** Monthly district extraction in Earth Engine → calendar-month anomaly standardization → threshold-and-run drought events (including one-month gap pooling, minimum two-month duration) → Spearman associations at 0–3 month lags with FDR correction → sensor, canal-proximity and exploratory wheat-yield comparisons.

## Findings from the research report

- **91 SPI-1 drought events** and **48 soil-moisture drought events** at the primary −1.0 threshold, across the analyzed districts.
- The four reported environmental associations had their strongest relationships at **zero-month lag**. This does **not** demonstrate causal propagation.
- No statistically significant wheat-yield or canal-interaction effects in the **three prespecified** regression specifications.
- Terra and Aqua daytime LST series were strongly correlated where both were observed, but this is **not independent ground validation**.

These figures and statistical statements are **reported findings from the original study**, not independently replicated results from a fresh environment.

## Results in figures

| Drought-event timing | Environmental associations |
| --- | --- |
| ![Drought-event timelines](figures/drought_event_timelines.png) | ![Multi-variable lag correlations](figures/lag_correlations_heatmap.png) |

| Multan multi-sensor time series | Canal proximity |
| --- | --- |
| ![Multan SPI, soil water and biophysical anomalies](figures/cascade_timeseries_Multan.png) | ![Cropland within canal buffers](figures/canal_exposure_map.png) |

[Terra–Aqua temperature consistency figure](figures/terra_aqua_annual_gap.png) · [All figures](figures/)

## Reproducibility and scientific limitations

The [notebook](notebooks/drought_study.ipynb) and [run guide](docs/RUNNING_THE_ANALYSIS.md) document the actual pipeline, its input folders and export/analysis flags. **A clean-environment rerun and independent reconciliation of every published result have not been demonstrated.**

- Source coverage differs across sensors (Aqua begins in mid-2002, for example); this is not a uniform direct-satellite 2001–2025 record.
- A mapped canal buffer is an **exposure proxy**, not actual water access or irrigation delivery.
- Some official wheat-yield observations required limited gap filling; only **11 district clusters** are available for regression inference.
- The report is observational and does not support causal crop-loss, irrigation-effect or event-propagation claims.
- The research assignment context is **not** affiliation or endorsement by AIRCAS/CAS.

## Research portfolio

[Fourth project: Spatiotemporal Urban Heat Vulnerability Assessment — Multan, Pakistan (2003–2023)](https://github.com/musab-shahid/multan-environmental-heat-screening) adds source-ID mapping and temporal model evaluation.

| Project | Focus | Research context |
| --- | --- | --- |
| [Spatiotemporal Analysis of Urban Heat Island Effect in Multan, Pakistan (2013–2023)](https://github.com/musab-shahid/multan-uhi-analysis) | Landsat LST and spectral indices | Undergraduate final-year research |
| [Monsoon Rainfall & Flood-Risk Analysis for Multan](https://github.com/musab-shahid/multan-era5-monsoon-analysis) | Time-series climate reanalysis and rainfall statistics | **Collaborative**, four contributors |
| **This project — Drought Event Analysis in South Punjab, Pakistan** | Multi-sensor event analysis and exploratory agricultural relationships | **Independent** research-application report |

## Citation

Shahid, M. (2026). *Drought Event Analysis in South Punjab, Pakistan: Multi-Sensor Remote Sensing of Precipitation, Soil Moisture, Vegetation and Thermal Cascades, and Exploratory Implications for Wheat Yield.* Unpublished research application report prepared for Dr. Chaolei Zheng, AIRCAS, Chinese Academy of Sciences.
