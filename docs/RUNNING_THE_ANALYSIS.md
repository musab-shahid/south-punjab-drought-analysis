# Running the analysis

## Existing exports: the tested route

Use Python 3.12 and the versions in `requirements.txt`. Get `Drought_Reproduction_Inputs.zip` from the [current Drive release](https://drive.google.com/drive/folders/1Nnk_-ldtT32jwGUrnzeHbKRUny1FVxGn). After extraction, pass the folder containing `gee_exports/` and `source_data/`:

```bash
python -m pip install -r requirements.txt
python scripts/run_analysis.py --inputs /path/to/reproduction_inputs --output /path/to/new_results
python -m unittest discover -s tests -v
```

The input bundle contains six environmental monthly CSVs, three canal-buffer CSVs, and the original wheat tables including source tags. Keep a copy of the bundle unchanged. The inherited pipeline copies the official wheat file to its working wheat filename inside `source_data/`; use an extracted working copy rather than the original archive.

The runner adapts paths and flags, disables Drive mounting and exports, and removes the unused Earth Engine import. Scientific functions run unchanged from `scripts/analysis.py`. The current scientific change relative to the original notebook is enforcement of the five-month Rabi minimum before the yield merge. Plot generation is disabled in this offline entrypoint because the inherited canal-map routine requests Earth Engine. Existing environmental figures remain valid because their tables did not change.

Outputs include the 3,300-row environmental panel, event catalogs, lag results, sensor checks, a 264-row eligible wheat panel, three primary-model summaries and nine buffer-model summaries. Original and current regression files must not be mixed.

## Fresh Earth Engine extraction: optional

The original `notebooks/drought_study.ipynb` documents export settings. For an updated run, use the corrected source in `scripts/analysis.py`, configure your Earth Engine project and Drive paths, and provide the canal GeoJSON. First run exports with `RUN_GEE_EXPORTS=True`, `RUN_ANALYSIS=False`; wait for completed exports. Then set exports false and analysis true. The tested reproduction above does not need this step.

The original executed Colab notebook remains in the Drive archive. Do not interpret old stored cell outputs as results from the corrected source.
