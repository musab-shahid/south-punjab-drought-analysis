# Data provenance and interpretation

The [original Drive archive](https://drive.google.com/drive/folders/1EFKdIpvvfyv1FfrVnsm2TWeDFcsamxs-) contains source documents, notebooks, exports and original outputs. The [current release](https://drive.google.com/drive/folders/1Nnk_-ldtT32jwGUrnzeHbKRUny1FVxGn) contains the revised report, corrected results and reproduction inputs. Original working paths are preserved.

`provenance/archive_manifest.json` records downloaded file names, byte counts, SHA-256 hashes and original Drive IDs. Resolve an ID as `https://drive.google.com/file/d/ID/view`. Hashes establish which files were used; they do not certify the source measurements.

## Environmental inputs

Six monthly export tables cover CHIRPS v3 precipitation, ERA5-Land depth-weighted soil water, MODIS Terra and Aqua daytime LST, MODIS NDVI and ET. The merged environmental panel has 3,300 district-month rows (11 districts × 300 months, 2001–2025). Aqua begins in July 2002; missing pre-launch values are not failed downloads. Three static canal-exposure tables contain the 2, 5 and 10 km cropland-buffer fractions.

The analysis uses the supplied exports unchanged. It does not verify every upstream cloud mask, polygon, product revision or extraction setting against a new provider extraction. ET composite-to-month allocation is approximate; satellite LST is surface temperature, and ERA5-Land soil moisture is modeled.

## Wheat sources

The source-tagged table contains 275 district/crop-year records, crop years 2000/01–2024/25, corresponding to harvest years 2001–2025. Its source labels are:

| Source label | Original records | Eligible regression records |
| --- | ---: | ---: |
| CRS_panel_2001_09 | 88 | 88 |
| PBS_yield_kg_ha_2007_20 | 121 | 121 |
| MNFSR_CRS_2021_25 | 44 | 44 |
| Kaggle_CRS_compiled_fill | 22 | 11 |

Gap-filled crop years are 2000/01 and 2020/21 in all 11 districts. The first is excluded by Rabi completeness; the second remains. These counts reconcile source labels, not a new line-by-line verification against all original government publications. File names ending `2000_2024` refer to crop-year start labels, not the final harvest year.

YLR is the standardized residual from each district's linear yield trend fitted over its supplied 25-year yield series; the regression eligibility filter is applied afterward. It is not a percentage yield loss or an attribution estimate.

## Statistical scope

The gamma/zero-probability SPI implementation is fitted by district and calendar month. Event thresholds are −0.5, −1.0 and −1.5; headline counts use only −1.0. Bridged months contribute duration but no deficit severity. Lag correlations are exploratory and autocorrelated; FDR adjustment does not remove that dependence. Canal proximity is not delivered water. Wheat models have only 11 district clusters and cannot establish causal irrigation or drought effects.
