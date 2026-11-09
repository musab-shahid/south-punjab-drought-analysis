# Drought Event Analysis in South Punjab, Pakistan

*Multi-Sensor Remote Sensing of Precipitation, Soil Moisture, Vegetation and Thermal Cascades, and Exploratory Implications for Wheat Yield*

**Musab Shahid · Independent research · 11 districts · 2001–2025**

This study combines CHIRPS, ERA5-Land and MODIS to characterize meteorological and soil-moisture drought, environmental associations, and exploratory wheat-yield relationships in South Punjab.

**[Read the full report](reports/Drought_Event_Analysis_South_Punjab_Report.pdf)** · [Portfolio case study](https://musab-shahid-earth-observation.brinycourt4.chatgpt.site/projects/south-punjab-drought-analysis.html) · [Current Drive release](https://drive.google.com/drive/folders/1Nnk_-ldtT32jwGUrnzeHbKRUny1FVxGn)

## Main findings

- **91 precipitation-drought events and 48 soil-moisture events** at the primary −1.0 threshold, using a minimum two-month duration and one-month gap pooling.
- Across the four environmental relationships, district-mean associations are strongest at **zero-month lag**. Wetter soil is associated with more vegetation and ET and lower surface temperature; temporal association does not establish causation.
- The three prespecified wheat models show **no statistically clear drought or canal-interaction association**. The current analysis uses **264 eligible district-years, harvest years 2002–2025**, with district and year fixed effects and 11 district clusters.
- Canal proximity is heterogeneous and buffer-sensitive. It describes mapped infrastructure proximity, not irrigation delivery.

![Drought event timelines](figures/drought_event_timelines.png)

## Explore the evidence

| Material | Contents |
| --- | --- |
| [Full report](reports/Drought_Event_Analysis_South_Punjab_Report.pdf) | Methods, maps, five figures, seven numbered tables, interpretation and references |
| [Result tables](data/outputs/) | Event catalogs, lag associations, sensor comparisons and corrected wheat models |
| [Figures](figures/) | Event timing, Multan time series, environmental associations, canal exposure and sensor comparison |
| [Run instructions](docs/RUNNING_THE_ANALYSIS.md) | Offline analysis from existing exports, plus the original Earth Engine workflow |
| [Current analysis](scripts/analysis.py) | Scientific pipeline with the documented Rabi completeness rule enforced |
| [Provenance](docs/PROVENANCE.md) | Input hashes, archive links, wheat source labels and coverage |
| [Original notebook](notebooks/drought_study.ipynb) | Historical extraction and analysis source, retained for traceability |

## Reproduce the analysis

Download the reproduction input bundle from the [current Drive release](https://drive.google.com/drive/folders/1Nnk_-ldtT32jwGUrnzeHbKRUny1FVxGn), extract it, and use Python 3.12:

```bash
python -m pip install -r requirements.txt
python scripts/run_analysis.py --inputs /path/to/reproduction_inputs --output /path/to/new_results
python -m unittest discover -s tests -v
```

No Earth Engine account is required for this CSV analysis. Drive access is separate from public GitHub and website access. See the run guide for the input folder layout.

The preserved analysis was rerun from its original exports: **all 12 CSV outputs matched** within numerical tolerance. The current release then fixes the previously unapplied five-month Rabi rule. Environmental results are unchanged; the wheat panel excludes the incomplete first season. [Release notes](docs/RELEASE_NOTES.md) document the change. Fresh satellite re-extraction and independent ground validation are not claimed.

## Scope and authorship

Musab Shahid carried out the data processing and analysis as a September 2026 research-application assignment prepared for Dr. Chaolei Zheng at AIRCAS, Chinese Academy of Sciences. This is not an institutional appointment or endorsement. The report acknowledges AI writing assistance during preparation; the November release also received coding, verification and editorial assistance.

ERA5-Land soil moisture is modeled reanalysis. Sensor coverage differs, ET monthly boundaries are approximated, monthly correlations are autocorrelated, and wheat data include documented gap filling. With only 11 clusters, regression inference is exploratory. [Methods and limitations](docs/PROVENANCE.md).

## Citation

Shahid, M. (2026). *Drought Event Analysis in South Punjab, Pakistan*. Unpublished research-application report, revised November 2026. Full subtitle and research context appear in the report.
