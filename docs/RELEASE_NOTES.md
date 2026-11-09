# November 2026 release

The original archive and notebook remain preserved. A local rerun of the historical analysis reproduced all 12 archived CSV tables with `rtol=1e-8`, `atol=1e-10`; see `provenance/original_output_comparison.json`. This checks the downstream analysis from preserved exports, not a fresh Earth Engine extraction.

## Corrected Rabi eligibility

The source declared `RABI_MIN_MONTHS = 5` but did not apply it. The current pipeline filters seasonal aggregates before merging with wheat yields. Harvest year 2001 has only four available months (January–April), so its 11 district records are excluded. The current panel has 264 rows across 2002–2025; every retained season has six soil-moisture months.

All three primary and nine buffer-model fits were rerun. No drought or interaction coefficient reaches p < 0.05. Environmental panels, event catalogs and lag associations are unchanged. The original 275-row results remain in the original Drive archive.

## Report corrections

The full report includes the current sample and regenerated Tables 5–6, explicit crop-year/harvest-year labels, the correct thermal-association direction, and six (rather than seven) top-ten events in the three lowest-canal-exposure districts. The separate seven-event count for Dera Ghazi Khan, Bahawalpur and Rajanpur was already correct. Original archive links are labeled historical; current tables live in this repository and the current Drive release.

## Verification

- Full historical analysis rerun and 12-table numerical comparison.
- Full corrected analysis rerun, including nine buffer-model fits.
- Environmental outputs unchanged; 264 unique eligible district-year records.
- Four passing tests covering gap pooling/severity, missing-data breaks, harvest-year alignment and release eligibility.
- Environment versions and source-file SHA-256 hashes recorded.
- Full report exported to PDF and visually reviewed.
