# SOUTH PUNJAB DROUGHT STUDY — CORRECTED END-TO-END PIPELINE (FIXED)
# AiRCAS / Dr. Chaolei Zheng research assignment
#
# Fixes applied relative to the previous V4 rewrite:
#   A. Aqua export crash: fc.first() was null → propertyNames() raised
#      EEException. Root cause: monthly_zonal_stats built a potentially
#      empty / non-materializable FC for Aqua when START_YEAR=2001 and
#      has_data filtering interacted with Algorithms.If on pre-July-2002
#      months. Aqua now starts at AQUA_START_YEAR=2002 and the pre-export
#      sanity check uses size() + limit(1) with an explicit null guard.
#   B. GAUL 2015 deprecation warning: prefer FAO/GAUL/2025/level2 with
#      automatic fallback to 2015 if district names/count do not match.
#   C. Drive mount noise: only mount when needed; suppress redundant message.
#   D. Robust empty-collection handling everywhere a .first() is used.
#   E. Explicit Aqua availability window (July 2002 onward).
#   F. Export integrity diagnostics unchanged; analysis block unchanged
#      except for safer loading paths.
#
# RUN MODEL — two Colab runs (exports are async; analysis needs finished CSVs)
# ------------------------------------------------------------------------------
# RUN 1 — exports:
#   RUN_GEE_EXPORTS = True
#   RUN_ANALYSIS    = False
#   → starts tasks into gee_exports/. Wait until all show COMPLETED in EE Tasks.
#
# RUN 2 — analysis + plots:
#   RUN_GEE_EXPORTS = False
#   RUN_ANALYSIS    = True
#   → reads gee_exports/, writes analysis_outputs/ (and figures/).
#
# Drive layout under AiRCAS_drought/:
#   gee_exports/        CHIRPS, ERA5, MODIS, canal exposure CSVs
#   source_data/        wheat panel, Kaggle raw, optional CRS PDFs/CSVs
#   analysis_outputs/   panels, events, lags, regression, figures/
#
# Wheat: Kaggle by default; spot-check vs CRS (see analysis notes). Optional
# OFFICIAL_WHEAT_CSV replaces Kaggle. Canal exposure uses cropland denominator.
# =============================================================================
# 0. CONFIGURATION
# =============================================================================
GEE_PROJECT = "drought-study"
# Root project folder on Google Drive.
PROJECT_DIR = "/content/drive/MyDrive/AiRCAS_drought/"
# Simple subfolders (created automatically if missing).
EXPORT_DIR = PROJECT_DIR + "gee_exports/"
ANALYSIS_DIR = PROJECT_DIR + "analysis_outputs/"
SOURCE_DIR = PROJECT_DIR + "source_data/"
FIGURES_DIR = ANALYSIS_DIR + "figures/"
# GEE toDrive folder name under My Drive.
# Use the project folder (proven reliable). Analysis always collects finished
# CSVs into gee_exports/ (from project root or gee_exports).
DRIVE_FOLDER = "AiRCAS_drought"
# Back-compat: GEE CSVs are read from EXPORT_DIR after collection.
DATA_DIR = EXPORT_DIR
START_YEAR = 2001
END_YEAR = 2025
# Aqua MYD11A2 begins 2002-07-04; use calendar year 2002 so monthly builder
# only requests months that can have data (pre-July months simply have size=0).
AQUA_START_YEAR = 2002
# --- TWO FLAGS (flip between Colab runs) ---
RUN_GEE_EXPORTS = False    # RUN 1: True  /  RUN 2: False
RUN_ANALYSIS = True      # RUN 1: False /  RUN 2: True
# Plots run with analysis (set False to skip figures).
RUN_PLOTS = True
# Canal-only re-export (optional). Leave False for normal full export.
RUN_CANAL_EXPORT_ONLY = False
# Official CRS/PBS/MNFSR panel — put this file in source_data/ on Drive.
OFFICIAL_WHEAT_CSV = SOURCE_DIR + "south_punjab_wheat_official_2000_2024.csv"
# "official" = required for final yield regression; "kaggle" = exploratory only.
WHEAT_SOURCE = "official"
# Fallback download only if official missing AND WHEAT_SOURCE allows kaggle.
PREPARE_WHEAT_FROM_KAGGLE = True
# Rabi season completeness: require this many months (of 6) for yield merge.
RABI_MIN_MONTHS = 5
# Optional: mount Drive in Colab when doing analysis or when reading uploads.
MOUNT_DRIVE = True
# District used for the cascade time-series figure.
PLOT_DISTRICT = "Multan"
# Static OSM-canal proximity parameter (primary analysis).
CANAL_BUFFER_M = 5000
# Extra buffers for sensitivity (appendix). Primary 5 km is always exported.
# Set empty tuple () to skip extra buffer exports / sensitivity regressions.
CANAL_BUFFER_SENSITIVITY_M = (2000, 10000)
# Canal GeoJSON on Drive (preferred). Put the file under AiRCAS_drought/
# e.g. "osm canals geojson/canals.geojson" or source_data/canals.geojson.
# If None or file missing, the loader searches common folders, then falls back
# to Colab upload.
CANAL_GEOJSON_PATH = PROJECT_DIR + "osm canals geojson/south_punjab_osm_canals.geojson"
# The study districts are the same 11 districts used in the original pipeline.
DISTRICTS = [
    "Multan District",
    "Khanewal District",
    "Vehari District",
    "Lodhran District",
    "Bahawalpur District",
    "Bahawalnagar District",
    "Rahim Yar Khan District",
    "Muzaffargarh District",
    "Layyah District",
    "Dera Ghazi Khan District",
    "Rajanpur District",
]
# Working path used by load_yield (official is copied here when present).
WHEAT_CSV = SOURCE_DIR + "south_punjab_wheat_2000_2024.csv"
KAGGLE_WHEAT_DATASET = (
    "muhammadsohaib15/punjab-district-wise-wheat-yield-and-production"
)
# =============================================================================
# 1. COLAB / GEE SETUP
# =============================================================================
import os
import json
import time
import shutil
import numpy as np
import pandas as pd


def ensure_project_dirs():
    """Create organised Drive subfolders if missing."""
    for d in (PROJECT_DIR, EXPORT_DIR, ANALYSIS_DIR, SOURCE_DIR, FIGURES_DIR):
        os.makedirs(d, exist_ok=True)


if MOUNT_DRIVE:
    try:
        from google.colab import drive
        # Avoid noisy "already mounted" message on re-runs.
        if not os.path.ismount("/content/drive"):
            drive.mount("/content/drive", force_remount=False)
        else:
            print("Drive already mounted at /content/drive.")
    except Exception as exc:
        print("Drive mount skipped/failed:", exc)
    ensure_project_dirs()

print(
    f"Mode: exports={RUN_GEE_EXPORTS}  analysis={RUN_ANALYSIS}  plots={RUN_PLOTS}"
)
print(f"gee_exports → {EXPORT_DIR}")
print(f"analysis_outputs → {ANALYSIS_DIR}")
print(f"source_data → {SOURCE_DIR}")

import ee
if RUN_GEE_EXPORTS or RUN_CANAL_EXPORT_ONLY:
    try:
        ee.Initialize(project=GEE_PROJECT)
        print("Earth Engine initialized.")
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)
        print("Earth Engine authenticated and initialized.")
    ensure_project_dirs()
    print("GEE exports will write to Drive folder:", DRIVE_FOLDER)
# =============================================================================
# 2. LOAD OSM CANALS
# =============================================================================
def _find_canal_geojson():
    """Resolve canal GeoJSON from config or common Drive locations."""
    candidates = []
    if CANAL_GEOJSON_PATH:
        candidates.append(CANAL_GEOJSON_PATH)
    # Common placements under AiRCAS_drought/
    for sub in (
        "osm canals geojson",
        "osm canals geoson",  # common typo
        "osm_canals_geojson",
        "source_data",
        "gee_exports",
        "",
    ):
        base = os.path.join(PROJECT_DIR, sub) if sub else PROJECT_DIR
        if not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            low = name.lower()
            if low.endswith((".geojson", ".json")) and (
                "canal" in low or "osm" in low or "waterway" in low
            ):
                candidates.append(os.path.join(base, name))
        # also any single .geojson in that folder
        for name in os.listdir(base):
            if name.lower().endswith(".geojson"):
                candidates.append(os.path.join(base, name))
    seen = set()
    for p in candidates:
        ap = os.path.abspath(p)
        if ap not in seen and os.path.isfile(ap):
            seen.add(ap)
            return ap
    return None


def load_canals_from_geojson(path=None):
    """
    Load the South Punjab OSM canal GeoJSON from Drive (preferred) or upload.
    Geometry is read directly from GeoJSON so LineString and other valid
    GeoJSON geometry types are handled more robustly than assuming LineString.
    """
    if path is None:
        path = _find_canal_geojson()
    if path is None:
        try:
            from google.colab import files
            print("No canal GeoJSON on Drive — use the upload picker.")
            uploaded = files.upload()
            if not uploaded:
                raise RuntimeError("No canal GeoJSON was uploaded.")
            path = next(iter(uploaded.keys()))
        except ImportError:
            raise FileNotFoundError(
                "Canal GeoJSON not found. Place a .geojson under "
                f"{PROJECT_DIR} (e.g. 'osm canals geojson/') or set "
                "CANAL_GEOJSON_PATH."
            )
    print("Loading canals from:", path)
    with open(path, encoding="utf-8") as f:
        geojson = json.load(f)
    features = []
    for feat in geojson.get("features", []):
        geom = feat.get("geometry")
        if not geom:
            continue
        features.append(
            ee.Feature(
                ee.Geometry(geom),
                feat.get("properties", {})
            )
        )
    if not features:
        raise ValueError("No valid canal geometries found in GeoJSON.")
    canals = ee.FeatureCollection(features)
    print("Canal features loaded:", canals.size().getInfo())
    return canals
# =============================================================================
# 3. DISTRICT BOUNDARIES / AOI
# =============================================================================
# Prefer GAUL 2025 (current); fall back to 2015 if names/count mismatch.
GAUL2_CANDIDATES = [
    "FAO/GAUL/2025/level2",
    "FAO/GAUL/2015/level2",
]
def get_aoi():
    last_error = None
    for asset_id in GAUL2_CANDIDATES:
        try:
            gaul = ee.FeatureCollection(asset_id)
            aoi = gaul.filter(
                ee.Filter.And(
                    ee.Filter.eq("ADM0_NAME", "Pakistan"),
                    ee.Filter.eq("ADM1_NAME", "Punjab"),
                    ee.Filter.inList("ADM2_NAME", DISTRICTS),
                )
            )
            count = aoi.size().getInfo()
            if count == len(DISTRICTS):
                print(f"Using GAUL asset: {asset_id} (districts={count})")
                return aoi, gaul
            found = aoi.aggregate_array("ADM2_NAME").getInfo()
            print(
                f"GAUL asset {asset_id}: expected {len(DISTRICTS)} districts, "
                f"found {count}: {found}"
            )
            last_error = ValueError(
                f"{asset_id} did not yield the expected 11 districts."
            )
        except Exception as exc:
            print(f"GAUL asset {asset_id} failed: {exc}")
            last_error = exc
    raise RuntimeError(
        "Could not build AOI from any GAUL candidate."
    ) from last_error
def validate_aoi(aoi):
    count = aoi.size().getInfo()
    print("District count:", count)
    if count != len(DISTRICTS):
        found = aoi.aggregate_array("ADM2_NAME").getInfo()
        raise ValueError(
            f"Expected {len(DISTRICTS)} districts but found {count}: {found}"
        )
    found = set(aoi.aggregate_array("ADM2_NAME").getInfo())
    missing = set(DISTRICTS) - found
    if missing:
        raise ValueError(f"Missing requested GAUL districts: {sorted(missing)}")
if RUN_GEE_EXPORTS or RUN_CANAL_EXPORT_ONLY:
    AOI, GAUL2 = get_aoi()
    validate_aoi(AOI)
# =============================================================================
# 4. GEE EXPORT HELPER
# =============================================================================
def export_table(fc, description):
    """
    Start a Drive CSV export into the project Drive folder.
    Analysis later collects these CSVs into gee_exports/.
    Exported features are geometry-free (no large .geo column).
    """
    ensure_project_dirs()
    task = ee.batch.Export.table.toDrive(
        collection=fc,
        description=description,
        folder=DRIVE_FOLDER,
        fileNamePrefix=description,
        fileFormat="CSV",
    )
    task.start()
    print(
        f"Started export: {description}  →  Drive/{DRIVE_FOLDER}/ "
        f"(analysis will collect into gee_exports/)"
    )
    return task
# =============================================================================
# 5. CANAL-EXPOSURE PROXY
# =============================================================================
#
# Definition (corrected):
#   area of ESA WorldCover cropland within 5 km of an OSM canal
#   --------------------------------------------------------------
#              total cropland area in the district
#
# = share of the district's cropland that is canal-exposed.
# This is a STATIC 2021 infrastructure-exposure proxy.
# It is NOT actual annual irrigated area and NOT proof that irrigation water
# reaches every cropland pixel inside the buffer.
#
# Also exported for reference:
#   canal_exposed_cropland_frac_of_district = exposed cropland / district area
#   (the previous formulation — kept only as a diagnostic column)
#
# Keep the 5-km choice as a stated parameter and test sensitivity (e.g. 2/5/10
# km) if time permits.
# =============================================================================
def build_canal_exposure(canals, aoi, buffer_m=5000):
    worldcover = (
        ee.ImageCollection("ESA/WorldCover/v200")
        .first()
        .select("Map")
    )
    cropland_mask = worldcover.eq(40)
    distance_to_canal = canals.distance(
        searchRadius=buffer_m + 1000,
        maxError=100,
    )
    in_buffer = distance_to_canal.lte(buffer_m).unmask(0)
    canal_exposed_cropland = (
        cropland_mask
        .multiply(in_buffer)
        .rename("canal_exposed_cropland")
    )
    pixel_area = ee.Image.pixelArea()
    exposed_area = (
        canal_exposed_cropland
        .multiply(pixel_area)
        .rename("canal_exposed_area_m2")
    )
    cropland_area_img = (
        cropland_mask
        .multiply(pixel_area)
        .rename("cropland_area_m2")
    )
    def per_district(feature):
        geom = feature.geometry()
        stats = (
            exposed_area.addBands(cropland_area_img)
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geom,
                scale=30,
                maxPixels=1e10,
                bestEffort=True,
                tileScale=4,
            )
        )
        exposed = ee.Number(stats.get("canal_exposed_area_m2"))
        cropland = ee.Number(stats.get("cropland_area_m2"))
        district_area = geom.area(maxError=100)
        # Primary: fraction of cropland that is canal-exposed
        frac_cropland = exposed.divide(cropland.max(1))
        # Legacy diagnostic: fraction of district area
        frac_district = exposed.divide(district_area)
        return feature.set({
            "district": feature.get("ADM2_NAME"),
            "canal_exposure_fraction": frac_cropland,
            "canal_exposed_cropland_frac_of_district": frac_district,
            # alias kept for older analysis code paths
            "irrigation_fraction": frac_cropland,
        })
    fc = aoi.map(per_district)
    print(
        fc.reduceColumns(
            ee.Reducer.toList(3),
            [
                "district",
                "canal_exposure_fraction",
                "canal_exposed_cropland_frac_of_district",
            ],
        ).getInfo()
    )
    return fc
def run_canal_exposure(canals, aoi, buffer_m=None, description=None):
    """
    Export canal-exposure fraction for one buffer distance.
    Primary (5 km) uses description district_canal_exposure_fraction.
    Sensitivity uses ..._2km / ..._10km suffixes.
    """
    buffer_m = CANAL_BUFFER_M if buffer_m is None else int(buffer_m)
    if description is None:
        if buffer_m == CANAL_BUFFER_M:
            description = "district_canal_exposure_fraction"
        else:
            # e.g. 2000 -> 2km, 10000 -> 10km
            km = buffer_m / 1000.0
            km_label = str(int(km)) if km == int(km) else str(km).replace(".", "p")
            description = f"district_canal_exposure_fraction_{km_label}km"
    fc = build_canal_exposure(canals, aoi, buffer_m=buffer_m)
    return export_table(
        fc.select(
            [
                "district",
                "canal_exposure_fraction",
                "canal_exposed_cropland_frac_of_district",
                "irrigation_fraction",
            ],
            None,
            False,
        ),
        description,
    )
# =============================================================================
# 6. MONTHLY IMAGE BUILDERS
# =============================================================================
def safe_empty_image(band_name):
    """
    Fully masked image carrying the expected band name.
    Used only when a monthly collection has no source images.
    """
    return (
        ee.Image.constant(0)
        .updateMask(ee.Image.constant(0))
        .rename(band_name)
    )
def monthly_collection_image(
    collection_id,
    start,
    end,
    source_band,
    output_band,
    reducer="mean",
    scale_factor=1.0,
    offset=0.0,
):
    """
    Build one monthly image and explicitly retain a has_data flag.
    This avoids the original Aqua problem by making the monthly image and its
    output band explicit before any district reduction.
    has_data is stored as an integer 0/1 so ee.Filter.eq is reliable.
    """
    coll = (
        ee.ImageCollection(collection_id)
        .filterDate(start, end)
        .select(source_band)
    )
    has_data = coll.size().gt(0)
    if reducer == "mean":
        source = coll.mean()
    elif reducer == "sum":
        source = coll.sum()
    else:
        raise ValueError("reducer must be 'mean' or 'sum'")
    valid = (
        source
        .multiply(scale_factor)
        .add(offset)
        .rename(output_band)
    )
    empty = safe_empty_image(output_band)
    image = ee.Image(
        ee.Algorithms.If(has_data, valid, empty)
    )
    # Store has_data as 0/1 integer for reliable client/server filtering.
    return image.set({
        "has_data": ee.Algorithms.If(has_data, 1, 0),
        "system:time_start": start.millis(),
    })
def chirps_month(y, m):
    start = ee.Date.fromYMD(y, m, 1)
    end = start.advance(1, "month")
    return monthly_collection_image(
        "UCSB-CHC/CHIRPS/V3/PENTAD",
        start,
        end,
        "precipitation",
        "precip_mm",
        reducer="sum",
    )
def era5land_month(y, m):
    start = ee.Date.fromYMD(y, m, 1)
    end = start.advance(1, "month")
    coll = (
        ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR")
        .filterDate(start, end)
    )
    has_data = coll.size().gt(0)
    img = ee.Image(
        ee.Algorithms.If(
            has_data,
            coll.first(),
            ee.Image.constant(0),
        )
    )
    sm = img.expression(
        "0.07*b1 + 0.21*b2 + 0.72*b3",
        {
            "b1": img.select("volumetric_soil_water_layer_1"),
            "b2": img.select("volumetric_soil_water_layer_2"),
            "b3": img.select("volumetric_soil_water_layer_3"),
        },
    ).rename("sm_0_100cm")
    empty = safe_empty_image("sm_0_100cm")
    sm = ee.Image(ee.Algorithms.If(has_data, sm, empty))
    return sm.set({
        "has_data": ee.Algorithms.If(has_data, 1, 0),
        "system:time_start": start.millis(),
    })
def terra_lst_month(y, m):
    start = ee.Date.fromYMD(y, m, 1)
    end = start.advance(1, "month")
    return monthly_collection_image(
        "MODIS/061/MOD11A2",
        start,
        end,
        "LST_Day_1km",
        "lst_c",
        reducer="mean",
        scale_factor=0.02,
        offset=-273.15,
    )
def aqua_lst_month(y, m):
    """
    Correct Aqua implementation.
    MYD11A2 has LST_Day_1km. MODIS LST is stored with a 0.02 K scale factor.
    Aqua begins in July 2002, so earlier months simply have no records.
    """
    start = ee.Date.fromYMD(y, m, 1)
    end = start.advance(1, "month")
    return monthly_collection_image(
        "MODIS/061/MYD11A2",
        start,
        end,
        "LST_Day_1km",
        "lst_c",
        reducer="mean",
        scale_factor=0.02,
        offset=-273.15,
    )
def ndvi_month(y, m):
    start = ee.Date.fromYMD(y, m, 1)
    end = start.advance(1, "month")
    return monthly_collection_image(
        "MODIS/061/MOD13Q1",
        start,
        end,
        "NDVI",
        "ndvi",
        reducer="mean",
        scale_factor=0.0001,
    )
def et_month(y, m):
    start = ee.Date.fromYMD(y, m, 1)
    end = start.advance(1, "month")
    return monthly_collection_image(
        "MODIS/061/MOD16A2GF",
        start,
        end,
        "ET",
        "et_mm",
        reducer="sum",
        scale_factor=0.1,
    )
# =============================================================================
# 7. MONTHLY DISTRICT REDUCTION
# =============================================================================
def monthly_zonal_stats(image_fn, aoi, start_year, end_year, scale, band_name):
    """
    Create one district-level record per available month.
    Missing source months are filtered out rather than creating fake values.
    The returned FeatureCollection always has the requested value property
    whenever at least one source month exists.
    has_data is stored as integer 0/1 so filtering is reliable.
    """
    n_months = (end_year - start_year + 1) * 12
    month_indices = ee.List.sequence(0, n_months - 1)
    def make_month_image(i):
        i = ee.Number(i)
        y = (
            ee.Number(start_year)
            .add(i.divide(12).floor())
        )
        m = i.mod(12).add(1)
        img = image_fn(y, m)
        return (
            img
            .set("year", y)
            .set("month", m)
        )
    images = ee.ImageCollection.fromImages(
        month_indices.map(make_month_image)
    ).filter(
        ee.Filter.eq("has_data", 1)
    )
    def reduce_one(img):
        img = ee.Image(img)
        stats = img.reduceRegions(
            collection=aoi,
            reducer=ee.Reducer.mean(),
            scale=scale,
            tileScale=4,
        )
        def tag(feature):
            return ee.Feature(None, {
                "district": feature.get("ADM2_NAME"),
                "year": img.get("year"),
                "month": img.get("month"),
                band_name: feature.get("mean"),
            })
        return stats.map(tag)
    return ee.FeatureCollection(
        images.map(reduce_one)
    ).flatten()
# =============================================================================
# 8. EXPORT FUNCTIONS
# =============================================================================
def run_chirps(aoi):
    fc = monthly_zonal_stats(
        chirps_month,
        aoi,
        START_YEAR,
        END_YEAR,
        5566,
        "precip_mm",
    )
    return export_table(fc, "CHIRPS_v3_monthly_district")
def run_era5land(aoi):
    fc = monthly_zonal_stats(
        era5land_month,
        aoi,
        START_YEAR,
        END_YEAR,
        11132,
        "sm_0_100cm",
    )
    return export_table(fc, "ERA5Land_SM_monthly_district")
def run_terra_lst(aoi):
    fc = monthly_zonal_stats(
        terra_lst_month,
        aoi,
        START_YEAR,
        END_YEAR,
        1000,
        "lst_c",
    )
    return export_table(fc, "MOD11A2_Terra_LST_monthly_district")
def _assert_fc_has_band(fc, band_name, label):
    """
    Safe pre-export sanity check.
    Uses size() + limit(1) so we never call propertyNames on a null element.
    """
    n = fc.size().getInfo()
    print(f"{label}: FeatureCollection size = {n}")
    if n == 0:
        raise RuntimeError(
            f"{label} EXPORT ABORTED: FeatureCollection is empty. "
            "No monthly images with has_data=1 were produced. "
            "Check collection ID, date range, and scale factors."
        )
    sample = fc.limit(1).getInfo()
    features = sample.get("features") or []
    if not features:
        raise RuntimeError(
            f"{label} EXPORT ABORTED: size() reported {n} but limit(1) "
            "returned no features (server materialization issue)."
        )
    props = features[0].get("properties") or {}
    print(f"{label} first feature properties:", props)
    if band_name not in props:
        raise RuntimeError(
            f"{label} EXPORT ABORTED: first feature does not contain "
            f"'{band_name}'. Properties are: {list(props.keys())}"
        )
    return props
def run_aqua_lst(aoi):
    """
    Canonical Aqua exporter.
    There is intentionally only ONE Aqua function and ONE execution call in
    this pipeline.
    Aqua is available from July 2002 onward. The export therefore begins at
    AQUA_START_YEAR (2002) rather than manufacturing 2001 data.
    Pre-export check uses size() + limit(1) and never calls propertyNames on
    a null first() element (the previous crash source).
    """
    fc = monthly_zonal_stats(
        aqua_lst_month,
        aoi,
        AQUA_START_YEAR,
        END_YEAR,
        1000,
        "lst_c",
    )
    _assert_fc_has_band(fc, "lst_c", "Aqua")
    return export_table(
        fc,
        "MYD11A2_Aqua_LST_monthly_district",
    )
def run_ndvi(aoi):
    fc = monthly_zonal_stats(
        ndvi_month,
        aoi,
        START_YEAR,
        END_YEAR,
        250,
        "ndvi",
    )
    return export_table(fc, "MOD13Q1_NDVI_monthly_district")
def run_et(aoi):
    fc = monthly_zonal_stats(
        et_month,
        aoi,
        START_YEAR,
        END_YEAR,
        500,
        "et_mm",
    )
    return export_table(fc, "MOD16A2GF_ET_monthly_district")
# =============================================================================
# 9. OPTIONAL DIRECT AQUA DIAGNOSTIC
# =============================================================================
def test_aqua_once(aoi):
    """
    This reproduces the successful diagnostic already established:
    January 2003 has Aqua images and district reduction produces lst_c.
    """
    collection = (
        ee.ImageCollection("MODIS/061/MYD11A2")
        .filterBounds(aoi)
        .filterDate("2003-01-01", "2003-02-01")
    )
    print("Aqua image count:", collection.size().getInfo())
    first = ee.Image(collection.first())
    print("Aqua bands:", first.bandNames().getInfo())
    lst_day_c = (
        first
        .select("LST_Day_1km")
        .multiply(0.02)
        .subtract(273.15)
    )
    aoi_result = lst_day_c.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=1000,
        maxPixels=1e9,
    )
    print("Aqua AOI January 2003:", aoi_result.getInfo())
    multan = (
        GAUL2
        .filter(ee.Filter.eq("ADM2_NAME", "Multan District"))
        .geometry()
    )
    district_result = lst_day_c.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=multan,
        scale=1000,
        maxPixels=1e9,
    )
    print("Aqua Multan January 2003:", district_result.getInfo())
# =============================================================================
# 10. START GEE EXPORTS
# =============================================================================
if RUN_CANAL_EXPORT_ONLY and not RUN_GEE_EXPORTS:
    # Corrected canal-exposure only (cropland denominator).
    canals = load_canals_from_geojson()
    run_canal_exposure(canals, AOI)  # primary
    for buf in CANAL_BUFFER_SENSITIVITY_M:
        if int(buf) == int(CANAL_BUFFER_M):
            continue
        run_canal_exposure(canals, AOI, buffer_m=int(buf))
    print(
        "\nCanal-exposure export started (denominator = total cropland). "
        "Wait for Drive task to finish, then set RUN_CANAL_EXPORT_ONLY=False "
        "and RUN_ANALYSIS=True."
    )
    try:
        task_list = ee.data.getTaskList()
        running = [t for t in task_list if t.get("state") in ("READY", "RUNNING")]
        print(f"Active tasks (READY/RUNNING): {len(running)}")
        for t in running[:10]:
            print(f"  {t.get('description')}: {t.get('state')}")
    except Exception as exc:
        print("Could not list tasks:", exc)

if RUN_GEE_EXPORTS:
    ensure_project_dirs()
    print(
        "Export destination: My Drive/"
        + DRIVE_FOLDER
        + "/  (CSVs land here when Tasks complete; "
        "analysis auto-copies them into gee_exports/)"
    )
    canals = load_canals_from_geojson()
    # Inspect Aqua once before launching all large exports.
    test_aqua_once(AOI)
    tasks = []
    tasks.append(run_canal_exposure(canals, AOI))  # primary 5 km
    for buf in CANAL_BUFFER_SENSITIVITY_M:
        if int(buf) == int(CANAL_BUFFER_M):
            continue
        tasks.append(run_canal_exposure(canals, AOI, buffer_m=int(buf)))
    tasks.append(run_chirps(AOI))
    tasks.append(run_era5land(AOI))
    tasks.append(run_terra_lst(AOI))
    tasks.append(run_aqua_lst(AOI))
    tasks.append(run_ndvi(AOI))
    tasks.append(run_et(AOI))
    print("\nAll GEE export tasks started.")
    # Prefer a compact task summary; getTaskList can be large.
    try:
        task_list = ee.data.getTaskList()
        running = [t for t in task_list if t.get("state") in ("READY", "RUNNING")]
        print(f"Active tasks (READY/RUNNING): {len(running)}")
        for t in running[:20]:
            print(f"  {t.get('description')}: {t.get('state')}")
    except Exception as exc:
        print("Could not list tasks:", exc)
# =============================================================================
# 11. ANALYSIS SETUP
# =============================================================================
if RUN_ANALYSIS:
    from scipy import stats as sps
    import statsmodels.formula.api as smf
    from statsmodels.stats.multitest import multipletests
    ensure_project_dirs()
    EXPORT_DIR = os.path.abspath(EXPORT_DIR)
    ANALYSIS_DIR = os.path.abspath(ANALYSIS_DIR)
    SOURCE_DIR = os.path.abspath(SOURCE_DIR)
    FIGURES_DIR = os.path.abspath(FIGURES_DIR)
    DATA_DIR = EXPORT_DIR  # GEE export CSVs
    WHEAT_CSV = os.path.join(SOURCE_DIR, "south_punjab_wheat_2000_2024.csv")
    OFFICIAL_WHEAT_CSV = os.path.join(
        SOURCE_DIR, "south_punjab_wheat_official_2000_2024.csv"
    )
    os.makedirs(EXPORT_DIR, exist_ok=True)
    # Preflight: expected GEE CSVs. EE often writes to AiRCAS_drought/ root
    # when the nested gee_exports folder was not the export target — collect
    # from root (and a few alternates) into EXPORT_DIR if needed.
    _expected = [
        "CHIRPS_v3_monthly_district.csv",
        "ERA5Land_SM_monthly_district.csv",
        "MOD11A2_Terra_LST_monthly_district.csv",
        "MYD11A2_Aqua_LST_monthly_district.csv",
        "MOD13Q1_NDVI_monthly_district.csv",
        "MOD16A2GF_ET_monthly_district.csv",
        "district_canal_exposure_fraction.csv",
        "district_irrigation_fraction.csv",
    ]
    _search_dirs = [
        EXPORT_DIR,
        PROJECT_DIR,
        os.path.join(PROJECT_DIR, "Data Exports (Inputs)"),
        os.path.join(PROJECT_DIR, "Data Exports (Inputs)/"),
    ]
    def _locate(fname):
        for d in _search_dirs:
            cand = os.path.join(d, fname)
            if os.path.isfile(cand):
                return cand
        return None
    _moved = []
    for fname in _expected:
        dest = os.path.join(EXPORT_DIR, fname)
        if os.path.isfile(dest):
            continue
        src = _locate(fname)
        if src and os.path.abspath(src) != os.path.abspath(dest):
            shutil.copy2(src, dest)
            _moved.append(fname)
            print(f"Copied export into gee_exports/: {fname}")
    if _moved:
        print(f"Collected {len(_moved)} export file(s) into {EXPORT_DIR}")
    _core = [f for f in _expected if not f.startswith("district_")]
    _missing = [f for f in _core if not os.path.isfile(os.path.join(EXPORT_DIR, f))]
    _has_canal = (
        os.path.isfile(os.path.join(EXPORT_DIR, "district_canal_exposure_fraction.csv"))
        or os.path.isfile(os.path.join(EXPORT_DIR, "district_irrigation_fraction.csv"))
    )
    if not _has_canal:
        _missing.append(
            "district_canal_exposure_fraction.csv "
            "(or district_irrigation_fraction.csv)"
        )
    if _missing:
        # Helpful listing of what IS in project root
        root_csvs = []
        if os.path.isdir(PROJECT_DIR):
            root_csvs = sorted(
                n for n in os.listdir(PROJECT_DIR) if n.lower().endswith(".csv")
            )[:30]
        raise FileNotFoundError(
            "Analysis preflight failed — missing under gee_exports/:\n  "
            + "\n  ".join(_missing)
            + "\nCSVs currently in AiRCAS_drought root: "
            + (", ".join(root_csvs) if root_csvs else "(none)")
            + "\nIf Tasks show COMPLETED, open Drive and move the export "
            "CSVs into gee_exports/, then re-run analysis."
        )
    print("Inputs  (exports):", EXPORT_DIR)
    print("Outputs (analysis):", ANALYSIS_DIR)
    print("Sources (wheat etc.):", SOURCE_DIR)
    if os.path.exists(OFFICIAL_WHEAT_CSV):
        print("Official wheat found:", OFFICIAL_WHEAT_CSV)
    else:
        print(
            "Official wheat NOT found at",
            OFFICIAL_WHEAT_CSV,
            "— will use Kaggle fallback if PREPARE_WHEAT_FROM_KAGGLE=True.",
        )
# =============================================================================
# 12. DISTRICT NAME HARMONIZATION
# =============================================================================
GAUL_TO_SHORT = {
    "Multan District": "Multan",
    "Khanewal District": "Khanewal",
    "Vehari District": "Vehari",
    "Lodhran District": "Lodhran",
    "Bahawalpur District": "Bahawalpur",
    "Bahawalnagar District": "Bahawalnagar",
    "Rahim Yar Khan District": "Rahim Yar Khan",
    "Muzaffargarh District": "Muzaffargarh",
    "Layyah District": "Layyah",
    "Dera Ghazi Khan District": "Dera Ghazi Khan",
    "Rajanpur District": "Rajanpur",
}
def harmonize(df, col="district"):
    df = df.copy()
    df[col] = (
        df[col]
        .astype(str)
        .str.strip()
        .replace(GAUL_TO_SHORT)
    )
    return df
# =============================================================================
# 13. STRICT GEE CSV VALIDATION
# =============================================================================
EXPECTED_EXPORTS = {
    "CHIRPS_v3_monthly_district.csv": "precip_mm",
    "ERA5Land_SM_monthly_district.csv": "sm_0_100cm",
    "MOD11A2_Terra_LST_monthly_district.csv": "lst_c",
    "MYD11A2_Aqua_LST_monthly_district.csv": "lst_c",
    "MOD13Q1_NDVI_monthly_district.csv": "ndvi",
    "MOD16A2GF_ET_monthly_district.csv": "et_mm",
}
REQUIRED_KEYS = ["district", "year", "month"]
def read_gee_csv_strict(path, value_col):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing export: {path}")
    df = pd.read_csv(path)
    required = REQUIRED_KEYS + [value_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"EXPORT INTEGRITY FAILURE\n"
            f"File: {path}\n"
            f"Missing: {missing}\n"
            f"Actual columns: {list(df.columns)}"
        )
    df = df[required].copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    if df[REQUIRED_KEYS].isna().any().any():
        raise ValueError(f"Null district/year/month keys in {path}")
    df["year"] = df["year"].astype(int)
    df["month"] = df["month"].astype(int)
    if not df["month"].between(1, 12).all():
        raise ValueError(f"Invalid month in {path}")
    duplicate_keys = df.duplicated(REQUIRED_KEYS).sum()
    if duplicate_keys:
        raise ValueError(
            f"{path} contains {duplicate_keys} duplicate district-year-month rows."
        )
    return harmonize(df)
def validate_export_set():
    print("\n=== EXPORT INTEGRITY AUDIT ===")
    reports = []
    for filename, value_col in EXPECTED_EXPORTS.items():
        path = os.path.join(DATA_DIR, filename)
        df = read_gee_csv_strict(path, value_col)
        reports.append({
            "file": filename,
            "rows": len(df),
            "districts": df["district"].nunique(),
            "min_year": df["year"].min(),
            "max_year": df["year"].max(),
            "non_null_value": int(df[value_col].notna().sum()),
            "null_value": int(df[value_col].isna().sum()),
        })
    irrigation_candidates = [
        "district_canal_exposure_fraction.csv",
        "district_irrigation_fraction.csv",
    ]
    irrigation_path = None
    for name in irrigation_candidates:
        candidate = os.path.join(DATA_DIR, name)
        if os.path.exists(candidate):
            irrigation_path = candidate
            break
    if irrigation_path is None:
        raise FileNotFoundError(
            "No canal-exposure/irrigation export found."
        )
    irr = pd.read_csv(irrigation_path)
    if "canal_exposure_fraction" not in irr.columns:
        if "irrigation_fraction" not in irr.columns:
            raise ValueError(
                f"Irrigation export has neither canal_exposure_fraction nor "
                f"irrigation_fraction. Columns: {list(irr.columns)}"
            )
        irr["canal_exposure_fraction"] = irr["irrigation_fraction"]
    irr = harmonize(irr)
    if irr["district"].nunique() != 11:
        raise ValueError(
            f"Expected 11 irrigation districts; found {irr['district'].nunique()}"
        )
    print(pd.DataFrame(reports).to_string(index=False))
    print("\nCanal exposure file:", os.path.basename(irrigation_path))
    print(irr[["district", "canal_exposure_fraction"]].sort_values("district"))
    # Aqua-specific verification.
    aqua_path = os.path.join(
        DATA_DIR,
        "MYD11A2_Aqua_LST_monthly_district.csv",
    )
    aqua = read_gee_csv_strict(aqua_path, "lst_c")
    if aqua["lst_c"].notna().sum() == 0:
        raise ValueError(
            "Aqua file has lst_c column but ZERO non-null LST values."
        )
    first_aqua_year = aqua.loc[aqua["lst_c"].notna(), "year"].min()
    first_aqua_month = aqua.loc[
        aqua["lst_c"].notna(), "month"
    ].iloc[0]
    print(
        f"\nAqua verified: lst_c present; first non-null record is "
        f"{int(first_aqua_year)}-{int(first_aqua_month):02d}."
    )
    return irr
# =============================================================================
# 14. LOAD + MERGE MONTHLY PANEL
# =============================================================================
def load_panel():
    irr = validate_export_set()
    precip = read_gee_csv_strict(
        os.path.join(DATA_DIR, "CHIRPS_v3_monthly_district.csv"),
        "precip_mm",
    )
    sm = read_gee_csv_strict(
        os.path.join(DATA_DIR, "ERA5Land_SM_monthly_district.csv"),
        "sm_0_100cm",
    )
    terra = read_gee_csv_strict(
        os.path.join(DATA_DIR, "MOD11A2_Terra_LST_monthly_district.csv"),
        "lst_c",
    ).rename(columns={"lst_c": "lst_terra_c"})
    aqua = read_gee_csv_strict(
        os.path.join(DATA_DIR, "MYD11A2_Aqua_LST_monthly_district.csv"),
        "lst_c",
    ).rename(columns={"lst_c": "lst_aqua_c"})
    ndvi = read_gee_csv_strict(
        os.path.join(DATA_DIR, "MOD13Q1_NDVI_monthly_district.csv"),
        "ndvi",
    )
    et = read_gee_csv_strict(
        os.path.join(DATA_DIR, "MOD16A2GF_ET_monthly_district.csv"),
        "et_mm",
    )
    keys = ["district", "year", "month"]
    panel = precip.merge(
        sm, on=keys, how="outer", validate="one_to_one"
    )
    panel = panel.merge(
        terra, on=keys, how="outer", validate="one_to_one"
    )
    panel = panel.merge(
        aqua, on=keys, how="outer", validate="one_to_one"
    )
    panel = panel.merge(
        ndvi, on=keys, how="outer", validate="one_to_one"
    )
    panel = panel.merge(
        et, on=keys, how="outer", validate="one_to_one"
    )
    panel = panel.merge(
        irr[["district", "canal_exposure_fraction"]],
        on="district",
        how="left",
        validate="many_to_one",
    )
    panel = panel.sort_values(keys).reset_index(drop=True)
    panel["date"] = pd.to_datetime(
        dict(
            year=panel["year"],
            month=panel["month"],
            day=1,
        )
    )
    print(
        f"\nPanel: {panel['district'].nunique()} districts × "
        f"{panel['date'].nunique()} unique monthly dates; "
        f"{len(panel)} rows."
    )
    print("\nNon-null coverage:")
    value_cols = [
        "precip_mm",
        "sm_0_100cm",
        "lst_terra_c",
        "lst_aqua_c",
        "ndvi",
        "et_mm",
    ]
    print(panel[value_cols].notna().sum())
    return panel
# =============================================================================
# 15. TERRA / AQUA CONSISTENCY CHECK
# =============================================================================
def terra_aqua_drift_check(panel):
    overlap = panel.dropna(
        subset=["lst_terra_c", "lst_aqua_c"]
    ).copy()
    if len(overlap) < 20:
        print("Insufficient Terra/Aqua overlap for comparison.")
        return pd.DataFrame()
    r, p = sps.pearsonr(
        overlap["lst_terra_c"],
        overlap["lst_aqua_c"],
    )
    overlap["terra_minus_aqua"] = (
        overlap["lst_terra_c"] -
        overlap["lst_aqua_c"]
    )
    yearly = (
        overlap
        .groupby("year")["terra_minus_aqua"]
        .mean()
        .reset_index()
    )
    if len(yearly) >= 3:
        slope, intercept = np.polyfit(
            yearly["year"],
            yearly["terra_minus_aqua"],
            1,
        )
    else:
        slope = np.nan
    result = pd.DataFrame([{
        "n_overlap": len(overlap),
        "pearson_r": r,
        "pearson_p": p,
        "mean_terra_minus_aqua_c":
            overlap["terra_minus_aqua"].mean(),
        "sd_terra_minus_aqua_c":
            overlap["terra_minus_aqua"].std(),
        "annual_gap_slope_c_per_year": slope,
    }])
    print("\n=== TERRA/AQUA CONSISTENCY ===")
    print(result.to_string(index=False))
    result.to_csv(
        os.path.join(ANALYSIS_DIR, "terra_aqua_consistency.csv"),
        index=False,
    )
    yearly.to_csv(
        os.path.join(ANALYSIS_DIR, "terra_aqua_annual_gap.csv"),
        index=False,
    )
    return result
# =============================================================================
# 16. SPI — MIXED DISTRIBUTION WITH ZERO PRECIPITATION
# =============================================================================
def compute_spi(panel, precip_col="precip_mm", window=1):
    """
    SPI-like implementation using:
      1. rolling precipitation,
      2. zero-probability q,
      3. gamma fit to positive precipitation,
      4. H(x) = q + (1-q)G(x),
      5. normal inverse transform.
    This avoids replacing all zero precipitation values with an arbitrary
    0.01 before gamma fitting.
    """
    df = panel.copy()
    roll_col = f"precip_roll{window}"
    spi_col = f"SPI{window}"
    df[roll_col] = (
        df.groupby("district")[precip_col]
        .transform(
            lambda s: s.rolling(
                window,
                min_periods=window,
            ).sum()
        )
    )
    df[spi_col] = np.nan
    for (district, month), idx in df.groupby(
        ["district", "month"]
    ).groups.items():
        vals = df.loc[idx, roll_col].dropna()
        if len(vals) < 10:
            continue
        positive = vals[vals > 0]
        if len(positive) < 5:
            continue
        q = float((vals <= 0).mean())
        try:
            shape, loc, scale = sps.gamma.fit(
                positive.values,
                floc=0,
            )
        except Exception:
            continue
        x = vals.values
        gamma_cdf = np.zeros_like(x, dtype=float)
        positive_mask = x > 0
        gamma_cdf[positive_mask] = sps.gamma.cdf(
            x[positive_mask],
            shape,
            loc=loc,
            scale=scale,
        )
        H = np.where(
            positive_mask,
            q + (1.0 - q) * gamma_cdf,
            q,
        )
        H = np.clip(H, 1e-6, 1 - 1e-6)
        spi = sps.norm.ppf(H)
        df.loc[vals.index, spi_col] = spi
    return df
# =============================================================================
# 17. CALENDAR-MONTH ANOMALY Z-SCORES
# =============================================================================
def add_zscores(panel, cols, min_obs=10):
    df = panel.copy()
    for col in cols:
        z_col = f"{col}_z"
        def zscore(s):
            valid = s.dropna()
            if len(valid) < min_obs:
                return pd.Series(
                    np.nan,
                    index=s.index,
                )
            sd = valid.std(ddof=1)
            if not np.isfinite(sd) or sd == 0:
                return pd.Series(
                    np.nan,
                    index=s.index,
                )
            return (s - valid.mean()) / sd
        df[z_col] = (
            df.groupby(["district", "month"])[col]
            .transform(zscore)
        )
    return df
# =============================================================================
# 18. DESCRIPTIVE VCI / TCI
# =============================================================================
def add_vci_tci(panel):
    df = panel.copy()
    for col, name, inverse in [
        ("ndvi", "VCI", False),
        ("lst_terra_c", "TCI", True),
    ]:
        group = df.groupby(
            ["district", "month"]
        )[col]
        cmin = group.transform("min")
        cmax = group.transform("max")
        denom = cmax - cmin
        if inverse:
            df[name] = (
                (cmax - df[col])
                / denom
                * 100
            )
        else:
            df[name] = (
                (df[col] - cmin)
                / denom
                * 100
            )
        df.loc[denom == 0, name] = np.nan
    return df
# =============================================================================
# 19. DROUGHT EVENT DETECTION
# =============================================================================
def extract_run_events(
    df,
    value_col,
    date_col="date",
    threshold=-1.0,
    gap_pool_limit=1,
    min_duration=2,
):
    """
    Run theory with one-month gap pooling.
    Corrections:
      - duration is inclusive: end - start + 1
      - NaN is treated as a data break, not silently skipped
      - an event at the end of the series is closed
      - severity sums only actual below-threshold deficits
    """
    values = df[value_col].to_numpy(dtype=float)
    dates = df[date_col].to_numpy()
    events = []
    in_event = False
    start_idx = None
    last_below_idx = None
    gap_count = 0
    deficit_sum = 0.0
    peak_intensity = np.inf
    def close_event(end_idx):
        nonlocal in_event
        nonlocal start_idx
        nonlocal last_below_idx
        nonlocal gap_count
        nonlocal deficit_sum
        nonlocal peak_intensity
        if start_idx is None or end_idx is None:
            return
        duration = end_idx - start_idx + 1
        if duration >= min_duration:
            events.append({
                "onset": dates[start_idx],
                "end": dates[end_idx],
                "duration_months": duration,
                "cumulative_severity": round(
                    deficit_sum,
                    3,
                ),
                "peak_intensity": round(
                    peak_intensity,
                    3,
                ),
            })
        in_event = False
        start_idx = None
        last_below_idx = None
        gap_count = 0
        deficit_sum = 0.0
        peak_intensity = np.inf
    for i, val in enumerate(values):
        if np.isnan(val):
            if in_event:
                close_event(last_below_idx)
            continue
        if val < threshold:
            if not in_event:
                in_event = True
                start_idx = i
                deficit_sum = threshold - val
                peak_intensity = val
            else:
                deficit_sum += threshold - val
                peak_intensity = min(
                    peak_intensity,
                    val,
                )
            last_below_idx = i
            gap_count = 0
        else:
            if not in_event:
                continue
            next_is_below = (
                i + 1 < len(values)
                and np.isfinite(values[i + 1])
                and values[i + 1] < threshold
            )
            if gap_count < gap_pool_limit and next_is_below:
                gap_count += 1
            else:
                close_event(last_below_idx)
    if in_event:
        close_event(last_below_idx)
    return pd.DataFrame(events)
def run_event_detection_all(
    panel,
    value_col,
    thresholds=(-0.5, -1.0, -1.5),
):
    all_events = []
    for district, group in panel.groupby("district"):
        group = group.sort_values("date")
        for threshold in thresholds:
            events = extract_run_events(
                group,
                value_col=value_col,
                threshold=threshold,
            )
            if len(events):
                events["district"] = district
                events["threshold"] = threshold
                events["indicator"] = value_col
                all_events.append(events)
    if not all_events:
        return pd.DataFrame()
    return pd.concat(
        all_events,
        ignore_index=True,
    )
# =============================================================================
# 20. EXPLORATORY LAG ASSOCIATIONS
# =============================================================================
def lag_correlations(
    panel,
    pairs,
    lags=(0, 1, 2, 3),
):
    """
    Spearman correlations on deseasonalized monthly anomalies.
    These are exploratory lag associations, NOT causal propagation tests.
    FDR corrects multiplicity but does not solve temporal autocorrelation.
    """
    results = []
    for district, group in panel.groupby("district"):
        group = (
            group
            .sort_values("date")
            .reset_index(drop=True)
        )
        for x_col, y_col, label in pairs:
            for lag in lags:
                if lag == 0:
                    x = group[x_col]
                    y = group[y_col]
                else:
                    x = group[x_col].iloc[:-lag]
                    y = group[y_col].iloc[lag:]
                mask = (
                    x.notna().to_numpy()
                    & y.notna().to_numpy()
                )
                if mask.sum() < 20:
                    continue
                r, p = sps.spearmanr(
                    x.to_numpy()[mask],
                    y.to_numpy()[mask],
                )
                results.append({
                    "district": district,
                    "pair": label,
                    "x": x_col,
                    "y": y_col,
                    "lag_months": lag,
                    "spearman_r": r,
                    "p_value": p,
                    "n": int(mask.sum()),
                })
    out = pd.DataFrame(results)
    if len(out):
        _, p_fdr, _, _ = multipletests(
            out["p_value"],
            alpha=0.05,
            method="fdr_bh",
        )
        out["p_fdr"] = p_fdr
        out["significant_fdr"] = (
            out["p_fdr"] < 0.05
        )
    return out
# =============================================================================
# 21. RABI HARVEST-YEAR ASSIGNMENT
# =============================================================================
def assign_rabi_harvest_year(panel):
    """
    Rabi season spans Nov-Apr.
    Nov-Dec belong to the following harvest year:
      Nov 2022 + Dec 2022 -> 2023 harvest
    Jan-Apr already belong to that harvest year:
      Jan 2023–Apr 2023 -> 2023 harvest
    This fixes the original year grouping, which otherwise excluded the
    preceding Nov-Dec from the same wheat harvest season.
    """
    df = panel.copy()
    df["rabi_harvest_year"] = np.where(
        df["month"].isin([11, 12]),
        df["year"] + 1,
        df["year"],
    )
    return df
# =============================================================================
# 22. WHEAT YIELD PANEL
# =============================================================================
def prepare_wheat_from_kaggle(
    out_csv=None,
    force=False,
):
    """
    Download Punjab district wheat panel from Kaggle and write a
    pipeline-ready CSV to Drive:
      district | crop_year | yield_t_per_ha

    Only runs under RUN_ANALYSIS. Safe to re-run: skips if out_csv exists
    unless force=True.
    """
    import shutil
    from pathlib import Path

    out_csv = out_csv or WHEAT_CSV
    if os.path.exists(out_csv) and not force:
        print(f"Wheat panel already on Drive: {out_csv} (skip Kaggle download)")
        return out_csv

    try:
        import kagglehub
    except ImportError:
        raise ImportError(
            "kagglehub is required for PREPARE_WHEAT_FROM_KAGGLE. "
            "In Colab run:  %pip install -q kagglehub"
        )

    print("Downloading Kaggle wheat dataset…")
    path = kagglehub.dataset_download(KAGGLE_WHEAT_DATASET)
    print("Kaggle cache path:", path)

    src_files = list(Path(path).rglob("*.csv")) + list(
        Path(path).rglob("*.xlsx")
    )
    print("Files found:", [str(p) for p in src_files])
    if not src_files:
        raise FileNotFoundError(f"No CSV/XLSX in {path}")

    src = src_files[0]
    raw_dst = os.path.join(
        SOURCE_DIR, "punjab_wheat_kaggle_raw" + src.suffix
    )
    os.makedirs(SOURCE_DIR, exist_ok=True)
    shutil.copy2(src, raw_dst)
    print("Raw copy on Drive:", raw_dst)

    if src.suffix.lower() == ".csv":
        raw = pd.read_csv(src)
    else:
        raw = pd.read_excel(src)

    print("Raw columns:", list(raw.columns))
    print(raw.head(3))

    def pick(colnames, *candidates):
        lower = {c.lower().strip(): c for c in colnames}
        for cand in candidates:
            if cand.lower() in lower:
                return lower[cand.lower()]
        for c in colnames:
            cl = c.lower()
            if any(k in cl for k in candidates):
                return c
        return None

    dcol = pick(raw.columns, "district", "District")
    ycol = pick(raw.columns, "year", "Year", "crop_year", "season")
    vcol = pick(
        raw.columns,
        "yield (tonnes_per_acre)",
        "yield_tonnes_per_acre",
        "tonnes_per_acre",
        "yield",
        "yield_tonnes",
    )
    if not all([dcol, ycol, vcol]):
        raise ValueError(
            f"Could not map wheat columns. Got: {list(raw.columns)}. "
            "Inspect the printed head and adjust pick() candidates."
        )

    study_short = [
        "Multan",
        "Khanewal",
        "Vehari",
        "Lodhran",
        "Bahawalpur",
        "Bahawalnagar",
        "Rahim Yar Khan",
        "Muzaffargarh",
        "Layyah",
        "Dera Ghazi Khan",
        "Rajanpur",
    ]

    w = raw[[dcol, ycol, vcol]].copy()
    w.columns = ["district", "crop_year", "yield_tonnes_per_acre"]
    w["district"] = w["district"].astype(str).str.strip()
    w["district"] = w["district"].replace({
        "D.G. Khan": "Dera Ghazi Khan",
        "D.G.Khan": "Dera Ghazi Khan",
        "DG Khan": "Dera Ghazi Khan",
        "Dera Ghazi Khan District": "Dera Ghazi Khan",
        "R.Y. Khan": "Rahim Yar Khan",
        "Rahimyar Khan": "Rahim Yar Khan",
        "R. Y. Khan": "Rahim Yar Khan",
        "Rahim Yar Khan District": "Rahim Yar Khan",
    })
    w = w[w["district"].isin(study_short)].copy()

    # tonnes/acre → t/ha
    w["yield_t_per_ha"] = (
        pd.to_numeric(w["yield_tonnes_per_acre"], errors="coerce")
        * 2.47105
    )

    def to_crop_year(v):
        s = str(v).strip()
        if "-" in s and len(s) >= 7:
            return s
        try:
            y = int(float(s))
            return f"{y}-{(y + 1) % 100:02d}"
        except Exception:
            return s

    w["crop_year"] = w["crop_year"].map(to_crop_year)
    w = w.dropna(subset=["yield_t_per_ha"])
    w = w[["district", "crop_year", "yield_t_per_ha"]].drop_duplicates()

    if w.empty:
        raise RuntimeError(
            "Wheat filter produced zero rows. Check district name mapping "
            "against the printed raw head."
        )

    w.to_csv(out_csv, index=False)
    print(f"Wrote {len(w)} rows → {out_csv}")
    print(w.groupby("district")["crop_year"].nunique())
    print(w.head())
    return out_csv


def load_yield(panel_districts):
    if not os.path.exists(WHEAT_CSV):
        raise FileNotFoundError(
            f"Wheat file not found: {WHEAT_CSV}. "
            "Set PREPARE_WHEAT_FROM_KAGGLE = True and re-run analysis."
        )
    yield_df = pd.read_csv(WHEAT_CSV)
    yield_df = harmonize(yield_df)
    required = [
        "district",
        "crop_year",
        "yield_t_per_ha",
    ]
    missing = [
        c for c in required
        if c not in yield_df.columns
    ]
    if missing:
        raise ValueError(
            f"Yield file missing columns: {missing}. "
            f"Actual: {list(yield_df.columns)}"
        )
    def parse_harvest_year(value):
        return int(str(value).split("-")[0]) + 1
    yield_df["harvest_year"] = (
        yield_df["crop_year"]
        .apply(parse_harvest_year)
    )
    yield_df["yield_t_per_ha"] = pd.to_numeric(
        yield_df["yield_t_per_ha"],
        errors="coerce",
    )
    def calc_ylr(group):
        group = group.sort_values(
            "harvest_year"
        ).copy()
        x = group["harvest_year"].to_numpy()
        y = group["yield_t_per_ha"].to_numpy()
        valid = np.isfinite(y)
        if valid.sum() >= 3:
            slope, intercept = np.polyfit(
                x[valid],
                y[valid],
                1,
            )
            residual = (
                y -
                (slope * x + intercept)
            )
            sd = np.nanstd(
                residual[valid],
                ddof=1,
            )
            if np.isfinite(sd) and sd > 0:
                group["YLR"] = residual / sd
            else:
                group["YLR"] = residual
        else:
            group["YLR"] = np.nan
        return group
    # Avoid pandas FutureWarning on grouping columns in apply.
    parts = []
    for _, g in yield_df.groupby("district", sort=False):
        parts.append(calc_ylr(g))
    yield_df = pd.concat(parts, ignore_index=True)
    missing_districts = (
        set(panel_districts)
        - set(yield_df["district"].unique())
    )
    if missing_districts:
        print(
            "WARNING — districts missing from yield data:",
            sorted(missing_districts),
        )
    n_years = yield_df["harvest_year"].nunique()
    print(
        f"Yield panel: {n_years} harvest years; "
        f"{len(yield_df)} rows."
    )
    # Soft gate: still return the panel so merged CSV can be written;
    # regression is skipped in the caller when years are too few.
    if n_years < 15:
        print(
            f"WARNING — REGRESSION SKIPPED: wheat yield file contains only "
            f"{n_years} harvest years (need ≥15). Replace WHEAT_CSV with the "
            f"extended district-year panel before running yield validation. "
            f"The wheat_drought_validation_panel.csv will still be written."
        )
        yield_df.attrs["regression_ok"] = False
    else:
        yield_df.attrs["regression_ok"] = True
    return yield_df
# =============================================================================
# 23. PANEL REGRESSION
# =============================================================================
def run_panel_regression(merged, drought_col="drought_metric", label="primary"):
    """
    District + harvest-year fixed effects.
    The interaction tests whether drought response differs with the static
    canal-exposure proxy (fraction of cropland within 5 km of canals).
    With only 11 districts, clustered p-values are treated as indicative,
    not confirmatory.
    """
    data = merged.copy()
    if drought_col != "drought_metric":
        if drought_col not in data.columns:
            raise ValueError(f"Missing drought column: {drought_col}")
        data["drought_metric"] = data[drought_col]
    required = [
        "YLR",
        "drought_metric",
        "canal_exposure_fraction",
        "district",
        "harvest_year",
    ]
    missing = [c for c in required if c not in data.columns]
    if missing:
        raise ValueError(f"Regression data missing: {missing}")
    data = data.dropna(subset=required).copy()
    if data["district"].nunique() < 5:
        raise RuntimeError(
            "Too few districts for the intended panel analysis."
        )
    model = smf.ols(
        formula=(
            "YLR ~ drought_metric "
            "+ drought_metric:canal_exposure_fraction "
            "+ C(district) + C(harvest_year)"
        ),
        data=data,
    )
    results = model.fit(
        cov_type="cluster",
        cov_kwds={"groups": data["district"]},
    )
    print(f"\n=== YIELD REGRESSION [{label}] drought={drought_col} ===")
    print(results.summary())
    print(
        "\nNOTE: standard errors are clustered over only "
        f"{data['district'].nunique()} districts. "
        "Treat p-values as indicative rather than confirmatory."
    )
    out_name = f"yield_panel_regression_{label}.txt"
    with open(
        os.path.join(ANALYSIS_DIR, out_name),
        "w",
        encoding="utf-8",
    ) as f:
        f.write(f"Model label: {label}\nDrought metric: {drought_col}\n\n")
        f.write(results.summary().as_text())
        f.write(
            "\n\nCaveat: only "
            f"{data['district'].nunique()} district clusters; "
            "cluster-robust inference is limited. "
            "Interpret as robustness of qualitative pattern, not causal proof."
        )
    # Coefficient snapshot for comparison table
    params = results.params
    bse = results.bse
    pvals = results.pvalues
    snap = {
        "label": label,
        "drought_col": drought_col,
        "n_obs": int(results.nobs),
        "drought_coef": float(params.get("drought_metric", np.nan)),
        "drought_se": float(bse.get("drought_metric", np.nan)),
        "drought_p": float(pvals.get("drought_metric", np.nan)),
        "interaction_coef": float(
            params.get("drought_metric:canal_exposure_fraction", np.nan)
        ),
        "interaction_se": float(
            bse.get("drought_metric:canal_exposure_fraction", np.nan)
        ),
        "interaction_p": float(
            pvals.get("drought_metric:canal_exposure_fraction", np.nan)
        ),
        "adj_r2": float(results.rsquared_adj),
    }
    return results, snap


def summarise_events_by_threshold(events, name):
    """Print and return counts by threshold; write primary (-1.0) catalog."""
    if events is None or len(events) == 0:
        print(f"{name}: no events")
        return pd.DataFrame()
    counts = (
        events.groupby("threshold")
        .size()
        .reindex([-0.5, -1.0, -1.5], fill_value=0)
    )
    print(f"\n{name} events by threshold:")
    for thr, n in counts.items():
        tag = { -0.5: "mild", -1.0: "primary (moderate)", -1.5: "severe" }.get(
            thr, ""
        )
        print(f"  threshold={thr:>5}: {int(n):4d}  {tag}")
    primary = events[events["threshold"] == -1.0].copy()
    primary_path = os.path.join(
        ANALYSIS_DIR, f"{name}_events_threshold_m1p0.csv"
    )
    primary.to_csv(primary_path, index=False)
    print(f"Primary catalog (threshold=-1.0): {len(primary)} → {primary_path}")
    return primary


def major_drought_years_table(spi_primary, sm_primary, top_n=10):
    """
    Rank events by cumulative severity (more negative deficit = more severe)
    and write a short table for the report.
    """
    frames = []
    for df, indicator in [
        (spi_primary, "SPI1"),
        (sm_primary, "SM_z"),
    ]:
        if df is None or len(df) == 0:
            continue
        t = df.copy()
        t["indicator"] = indicator
        frames.append(t)
    if not frames:
        return pd.DataFrame()
    all_e = pd.concat(frames, ignore_index=True)
    # cumulative_severity is sum of (threshold - value) → larger = worse
    all_e = all_e.sort_values(
        "cumulative_severity", ascending=False
    ).head(top_n)
    cols = [
        c
        for c in [
            "district",
            "indicator",
            "threshold",
            "onset",
            "end",
            "duration_months",
            "cumulative_severity",
            "peak_intensity",
        ]
        if c in all_e.columns
    ]
    out = all_e[cols].reset_index(drop=True)
    path = os.path.join(ANALYSIS_DIR, "major_drought_events_top10.csv")
    out.to_csv(path, index=False)
    print("\n=== MAJOR DROUGHT EVENTS (top by cumulative severity) ===")
    print(out.to_string(index=False))
    print("Saved:", path)
    return out
# =============================================================================
# 24. RUN ANALYSIS
# =============================================================================
if RUN_ANALYSIS:
    print("\n==============================")
    print("LOADING GEE EXPORTS")
    print("==============================")
    panel = load_panel()
    # Terra/Aqua comparison.
    terra_aqua_drift_check(panel)
    # Drought/climate metrics.
    panel = compute_spi(
        panel,
        window=1,
    )
    panel = compute_spi(
        panel,
        window=3,
    )
    # Calendar-month anomalies.
    panel = add_zscores(
        panel,
        [
            "sm_0_100cm",
            "lst_terra_c",
            "ndvi",
            "et_mm",
        ],
    )
    # Descriptive indicators only.
    panel = add_vci_tci(panel)
    panel["season"] = np.where(
        panel["month"].isin([11, 12, 1, 2, 3, 4]),
        "Rabi",
        "Kharif",
    )
    panel = assign_rabi_harvest_year(panel)
    # -------------------------------------------------------------------------
    # Drought event catalogs
    # Thresholds: -0.5 mild | -1.0 primary (moderate) | -1.5 severe
    # Headline counts are reported BY THRESHOLD; primary catalog = -1.0 only.
    # -------------------------------------------------------------------------
    spi_events = run_event_detection_all(
        panel,
        value_col="SPI1",
        thresholds=(-0.5, -1.0, -1.5),
    )
    sm_events = run_event_detection_all(
        panel,
        value_col="sm_0_100cm_z",
        thresholds=(-0.5, -1.0, -1.5),
    )
    spi_events.to_csv(
        os.path.join(ANALYSIS_DIR, "SPI1_drought_events.csv"),
        index=False,
    )
    sm_events.to_csv(
        os.path.join(ANALYSIS_DIR, "SM_drought_events.csv"),
        index=False,
    )
    spi_primary = summarise_events_by_threshold(spi_events, "SPI1")
    sm_primary = summarise_events_by_threshold(sm_events, "SM")
    major_drought_years_table(spi_primary, sm_primary, top_n=10)
    # -------------------------------------------------------------------------
    # Lag analysis (exploratory associations — not causal propagation tests)
    # Report direction, magnitude of r_s, lag at peak association, and
    # cross-district consistency. Do not over-interpret FDR p-values given
    # temporal autocorrelation in monthly climate series.
    # -------------------------------------------------------------------------
    lag_pairs = [
        (
            "SPI1",
            "sm_0_100cm_z",
            "Precipitation drought -> Soil-water anomaly",
        ),
        (
            "sm_0_100cm_z",
            "lst_terra_c_z",
            "Soil-water anomaly -> Thermal anomaly",
        ),
        (
            "sm_0_100cm_z",
            "ndvi_z",
            "Soil-water anomaly -> NDVI anomaly",
        ),
        (
            "sm_0_100cm_z",
            "et_mm_z",
            "Soil-water anomaly -> ET anomaly",
        ),
    ]
    lag_df = lag_correlations(
        panel,
        lag_pairs,
        lags=(0, 1, 2, 3),
    )
    lag_df.to_csv(
        os.path.join(
            ANALYSIS_DIR,
            "lag_correlations_anomaly_based.csv",
        ),
        index=False,
    )
    if len(lag_df):
        peak = (
            lag_df.groupby("pair")
            .apply(
                lambda g: g.loc[g["spearman_r"].abs().idxmax()],
                include_groups=False,
            )
            if hasattr(lag_df.groupby("pair"), "apply")
            else lag_df
        )
        try:
            peak_rows = []
            for pair, g in lag_df.groupby("pair"):
                i = g["spearman_r"].abs().idxmax()
                peak_rows.append(g.loc[i])
            peak_df = pd.DataFrame(peak_rows)[
                ["pair", "lag_months", "spearman_r"]
            ]
            # District-mean peak lag summary
            mean_by_lag = (
                lag_df.groupby(["pair", "lag_months"])["spearman_r"]
                .mean()
                .reset_index()
            )
            best = mean_by_lag.loc[
                mean_by_lag.groupby("pair")["spearman_r"].apply(
                    lambda s: s.abs().idxmax()
                )
            ]
            print(
                "\nLag associations (district-mean |r|_max lag) — "
                "descriptive only, not causal:"
            )
            print(best.to_string(index=False))
        except Exception as exc:
            print("Lag peak summary skipped:", exc)
    # -------------------------------------------------------------------------
    # Save analysis panel
    # -------------------------------------------------------------------------
    panel.to_csv(
        os.path.join(
            ANALYSIS_DIR,
            "south_punjab_drought_analysis_panel.csv",
        ),
        index=False,
    )
    # -------------------------------------------------------------------------
    # Wheat validation
    # -------------------------------------------------------------------------
    # Prefer official CRS/PBS/MNFSR panel; else Kaggle fallback.
    if OFFICIAL_WHEAT_CSV and os.path.exists(OFFICIAL_WHEAT_CSV):
        os.makedirs(SOURCE_DIR, exist_ok=True)
        shutil.copy2(OFFICIAL_WHEAT_CSV, WHEAT_CSV)
        print("Using official wheat panel:", OFFICIAL_WHEAT_CSV)
    elif PREPARE_WHEAT_FROM_KAGGLE:
        prepare_wheat_from_kaggle(out_csv=WHEAT_CSV, force=False)
        print(
            "NOTE: official wheat file missing — used Kaggle fallback. "
            "Upload south_punjab_wheat_official_2000_2024.csv to source_data/ "
            "for the CRS/PBS/MNFSR panel."
        )
    else:
        raise FileNotFoundError(
            f"No wheat panel. Place official CSV at {OFFICIAL_WHEAT_CSV} "
            "or set PREPARE_WHEAT_FROM_KAGGLE=True."
        )

    yield_df = load_yield(
        panel["district"].unique()
    )
    regression_ok = bool(yield_df.attrs.get("regression_ok", False))
    # Rabi drought metrics (Nov–Apr aligned to harvest year):
    #   A (primary): mean SM z-score
    #   B: mean SPI-1
    #   C: mean SPI-3
    rabi = panel[
        panel["season"] == "Rabi"
    ].copy()
    rabi_district_year = (
        rabi
        .groupby(
            ["district", "rabi_harvest_year"],
            as_index=False,
        )
        .agg(
            drought_metric=("sm_0_100cm_z", "mean"),
            SPI1_mean=("SPI1", "mean"),
            SPI3_mean=("SPI3", "mean"),
            n_months=("sm_0_100cm_z", "count"),
        )
        .rename(
            columns={"rabi_harvest_year": "harvest_year"}
        )
    )
    # Enforce the documented minimum before merging or fitting any model.
    rabi_district_year = rabi_district_year.loc[
        rabi_district_year["n_months"] >= RABI_MIN_MONTHS
    ].copy()
    merged = yield_df.merge(
        rabi_district_year,
        on=["district", "harvest_year"],
        how="inner",
    )
    exposure = (
        panel[
            [
                "district",
                "canal_exposure_fraction",
            ]
        ]
        .drop_duplicates()
    )
    merged = merged.merge(
        exposure,
        on="district",
        how="left",
        validate="many_to_one",
    )
    merged.to_csv(
        os.path.join(
            ANALYSIS_DIR,
            "wheat_drought_validation_panel.csv",
        ),
        index=False,
    )
    print(
        f"Wheat–drought merge: {len(merged)} rows "
        f"({merged['district'].nunique()} districts, "
        f"{merged['harvest_year'].nunique()} harvest years)."
    )
    if regression_ok:
        # Three pre-specified robustness specs (not a specification search).
        snaps = []
        for label, col in [
            ("A_SM_z", "drought_metric"),
            ("B_SPI1", "SPI1_mean"),
            ("C_SPI3", "SPI3_mean"),
        ]:
            try:
                _, snap = run_panel_regression(
                    merged, drought_col=col, label=label
                )
                snaps.append(snap)
            except Exception as exc:
                print(f"Regression [{label}] failed:", exc)
        if snaps:
            snap_df = pd.DataFrame(snaps)
            snap_path = os.path.join(
                ANALYSIS_DIR, "yield_regression_robustness_summary.csv"
            )
            snap_df.to_csv(snap_path, index=False)
            print("\n=== YIELD ROBUSTNESS SUMMARY ===")
            print(snap_df.to_string(index=False))
            print("Saved:", snap_path)
            # Also keep a primary alias of model A text
            primary_txt = os.path.join(
                ANALYSIS_DIR, "yield_panel_regression_A_SM_z.txt"
            )
            alias = os.path.join(
                ANALYSIS_DIR, "yield_panel_regression_summary.txt"
            )
            if os.path.exists(primary_txt):
                shutil.copy2(primary_txt, alias)

        # -----------------------------------------------------------------
        # Canal-buffer sensitivity (2 km / 10 km vs primary 5 km)
        # Appendix only: same drought metrics, alternate exposure maps.
        # -----------------------------------------------------------------
        if CANAL_BUFFER_SENSITIVITY_M:
            print("\n=== CANAL BUFFER SENSITIVITY ===")
            sens_snaps = []
            # Primary 5 km already in snaps; re-load alternate exposure files
            buffer_files = {
                int(CANAL_BUFFER_M): "district_canal_exposure_fraction.csv",
            }
            for buf in CANAL_BUFFER_SENSITIVITY_M:
                buf = int(buf)
                if buf == int(CANAL_BUFFER_M):
                    continue
                km = buf / 1000.0
                km_label = str(int(km)) if km == int(km) else str(km).replace(".", "p")
                buffer_files[buf] = f"district_canal_exposure_fraction_{km_label}km.csv"

            def _find_export(fname):
                for d in (EXPORT_DIR, PROJECT_DIR):
                    cand = os.path.join(d, fname)
                    if os.path.isfile(cand):
                        if os.path.abspath(d) != os.path.abspath(EXPORT_DIR):
                            dest = os.path.join(EXPORT_DIR, fname)
                            shutil.copy2(cand, dest)
                            return dest
                        return cand
                return None

            for buf, fname in buffer_files.items():
                path = _find_export(fname)
                if path is None:
                    print(f"  skip {buf}m — missing {fname}")
                    continue
                exp = pd.read_csv(path)
                if "canal_exposure_fraction" not in exp.columns:
                    if "irrigation_fraction" in exp.columns:
                        exp["canal_exposure_fraction"] = exp["irrigation_fraction"]
                    else:
                        print(f"  skip {buf}m — no exposure column in {fname}")
                        continue
                exp = harmonize(exp)
                m2 = merged.drop(columns=["canal_exposure_fraction"], errors="ignore")
                m2 = m2.merge(
                    exp[["district", "canal_exposure_fraction"]],
                    on="district",
                    how="left",
                    validate="many_to_one",
                )
                km_label = (
                    str(int(buf / 1000)) if buf % 1000 == 0 else str(buf)
                )
                for drought_label, col in [
                    ("A_SM_z", "drought_metric"),
                    ("B_SPI1", "SPI1_mean"),
                    ("C_SPI3", "SPI3_mean"),
                ]:
                    try:
                        _, snap = run_panel_regression(
                            m2,
                            drought_col=col,
                            label=f"buf{km_label}km_{drought_label}",
                        )
                        snap["buffer_m"] = buf
                        sens_snaps.append(snap)
                    except Exception as exc:
                        print(f"  regression buf{km_label}km/{drought_label} failed:", exc)

            if sens_snaps:
                sens_df = pd.DataFrame(sens_snaps)
                sens_path = os.path.join(
                    ANALYSIS_DIR, "yield_regression_buffer_sensitivity.csv"
                )
                sens_df.to_csv(sens_path, index=False)
                print(sens_df.to_string(index=False))
                print("Saved:", sens_path)
            else:
                print(
                    "No buffer-sensitivity regressions run "
                    "(export 2km/10km canal files first, or set "
                    "CANAL_BUFFER_SENSITIVITY_M = ())."
                )
    else:
        print(
            "Panel regression not run (insufficient harvest years). "
            "All other analysis outputs were written successfully."
        )
    print("\n==============================")
    print("ANALYSIS COMPLETE")
    print("==============================")
    print(
        "Analysis outputs written to:",
        ANALYSIS_DIR,
    )
    print(
        "GEE export inputs read from:",
        EXPORT_DIR,
    )

# =============================================================================
# 25. FIGURES (optional — uses saved CSVs; does not re-export GEE)
# =============================================================================
#
# Controlled by RUN_PLOTS. Safe to run after analysis, or alone if outputs
# already exist on Drive. Writes PNGs to DATA_DIR/figures/.
#
# Fixes vs the ad-hoc notebook cells:
#   - No redefinition of load_panel / lag_correlations / GAUL helpers
#   - Event timelines filter to threshold == -1.0 (matches titles)
#   - Lag figure is a heatmap summary, not a full table dump
#   - Canal map uses EE→GeoJSON once; labels use representative points
#   - All figures saved to Drive, not only shown in Colab
# =============================================================================

def _figures_dir():
    d = FIGURES_DIR
    os.makedirs(d, exist_ok=True)
    return d


def plot_canal_exposure_map():
    """Choropleth of canal_exposure_fraction for the 11 districts."""
    import matplotlib.pyplot as plt
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise ImportError(
            "geopandas required for canal map. "
            "In Colab: %pip install -q geopandas"
        ) from exc

    # Need EE only for boundaries
    try:
        ee.Initialize(project=GEE_PROJECT)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT)

    aoi, _ = get_aoi()
    geojson_data = aoi.getInfo()
    gdf = gpd.GeoDataFrame.from_features(geojson_data["features"])
    gdf["district"] = gdf["ADM2_NAME"].replace(GAUL_TO_SHORT)

    canal_path = os.path.join(DATA_DIR, "district_canal_exposure_fraction.csv")
    if not os.path.exists(canal_path):
        alt = os.path.join(DATA_DIR, "district_irrigation_fraction.csv")
        canal_path = alt if os.path.exists(alt) else canal_path
    canal = harmonize(pd.read_csv(canal_path))
    if "canal_exposure_fraction" not in canal.columns:
        canal["canal_exposure_fraction"] = canal["irrigation_fraction"]

    gdf = gdf.merge(
        canal[["district", "canal_exposure_fraction"]],
        on="district",
        how="left",
    )

    fig, ax = plt.subplots(1, 1, figsize=(11, 9))
    gdf.plot(
        column="canal_exposure_fraction",
        cmap="YlGnBu",
        linewidth=0.8,
        ax=ax,
        edgecolor="0.35",
        legend=True,
        legend_kwds={"label": "Canal exposure fraction", "shrink": 0.7},
        missing_kwds={"color": "lightgrey"},
    )
    # Representative points avoid geographic centroid issues on multipolygons
    for _, row in gdf.iterrows():
        pt = row.geometry.representative_point()
        ax.annotate(
            row["district"],
            xy=(pt.x, pt.y),
            xytext=(0, 0),
            textcoords="offset points",
            fontsize=7,
            ha="center",
            va="center",
            color="black",
        )
    ax.set_title("South Punjab — canal exposure fraction (5 km OSM buffer)")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal")
    plt.tight_layout()
    out = os.path.join(_figures_dir(), "canal_exposure_map.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.show()
    plt.close(fig)
    print("Saved:", out)


def plot_drought_event_timelines():
    """Yearly counts of SPI1 and SM events at threshold = -1.0."""
    import matplotlib.pyplot as plt

    spi_path = os.path.join(ANALYSIS_DIR, "SPI1_drought_events.csv")
    sm_path = os.path.join(ANALYSIS_DIR, "SM_drought_events.csv")
    spi = pd.read_csv(spi_path)
    sm = pd.read_csv(sm_path)
    spi["onset"] = pd.to_datetime(spi["onset"])
    sm["onset"] = pd.to_datetime(sm["onset"])
    # Match figure titles: moderate drought threshold
    if "threshold" in spi.columns:
        spi = spi[spi["threshold"] == -1.0]
    if "threshold" in sm.columns:
        sm = sm[sm["threshold"] == -1.0]
    spi_y = (
        spi.assign(year=spi["onset"].dt.year)
        .groupby("year")
        .size()
        .reindex(range(START_YEAR, END_YEAR + 1), fill_value=0)
    )
    sm_y = (
        sm.assign(year=sm["onset"].dt.year)
        .groupby("year")
        .size()
        .reindex(range(START_YEAR, END_YEAR + 1), fill_value=0)
    )

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    ax1.bar(spi_y.index, spi_y.values, color="steelblue", width=0.8)
    ax1.set_title("SPI1 drought events per year (threshold = −1.0)")
    ax1.set_ylabel("Event count")
    ax1.grid(axis="y", linestyle="--", alpha=0.5)

    ax2.bar(sm_y.index, sm_y.values, color="darkorange", width=0.8)
    ax2.set_title("Soil-moisture anomaly events per year (threshold = −1.0)")
    ax2.set_xlabel("Year")
    ax2.set_ylabel("Event count")
    ax2.grid(axis="y", linestyle="--", alpha=0.5)
    plt.xticks(rotation=45)
    plt.tight_layout()
    out = os.path.join(_figures_dir(), "drought_event_timelines.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.show()
    plt.close(fig)
    print("Saved:", out)


def plot_cascade_timeseries(district=None):
    """
    SPI → SM → NDVI / LST / ET anomalies for one district.
    Prefers the saved analysis panel; falls back to rebuilding metrics.
    """
    import matplotlib.pyplot as plt

    district = district or PLOT_DISTRICT
    panel_path = os.path.join(
        ANALYSIS_DIR, "south_punjab_drought_analysis_panel.csv"
    )
    if os.path.exists(panel_path):
        panel = pd.read_csv(panel_path, parse_dates=["date"])
    else:
        panel = load_panel()
        panel = compute_spi(panel, window=1)
        panel = add_zscores(
            panel, ["sm_0_100cm", "lst_terra_c", "ndvi", "et_mm"]
        )
        panel["date"] = pd.to_datetime(
            dict(year=panel["year"], month=panel["month"], day=1)
        )

    needed = ["SPI1", "sm_0_100cm_z", "ndvi_z", "lst_terra_c_z", "et_mm_z"]
    missing = [c for c in needed if c not in panel.columns]
    if missing:
        raise ValueError(
            f"Panel missing {missing}. Re-run with RUN_ANALYSIS = True."
        )

    df = (
        panel[panel["district"] == district]
        .sort_values("date")
        .reset_index(drop=True)
    )
    if df.empty:
        raise ValueError(f"No rows for district={district!r}")

    titles = {
        "SPI1": "SPI-1 (precip. drought)",
        "sm_0_100cm_z": "Soil moisture anomaly (z)",
        "ndvi_z": "NDVI anomaly (z)",
        "lst_terra_c_z": "Terra LST anomaly (z)",
        "et_mm_z": "ET anomaly (z)",
    }
    fig, axes = plt.subplots(
        len(needed), 1, figsize=(13, 2.2 * len(needed)), sharex=True
    )
    for ax, col in zip(axes, needed):
        ax.plot(df["date"], df[col], lw=0.9, color="C0")
        ax.axhline(0, color="gray", ls="--", lw=0.8)
        ax.set_ylabel(titles[col], fontsize=9)
        ax.grid(True, ls=":", alpha=0.5)
    axes[-1].set_xlabel("Date")
    fig.suptitle(
        f"Drought cascade — {district}",
        fontsize=13,
        y=0.995,
    )
    plt.tight_layout()
    out = os.path.join(
        _figures_dir(), f"cascade_timeseries_{district.replace(' ', '_')}.png"
    )
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.show()
    plt.close(fig)
    print("Saved:", out)


def plot_lag_heatmap():
    """Mean Spearman r across districts by lag and pair (from saved CSV)."""
    import matplotlib.pyplot as plt

    lag_path = os.path.join(ANALYSIS_DIR, "lag_correlations_anomaly_based.csv")
    if not os.path.exists(lag_path):
        raise FileNotFoundError(
            f"Missing {lag_path}. Run analysis first (RUN_ANALYSIS = True)."
        )
    lag = pd.read_csv(lag_path)
    if lag.empty:
        print("Lag CSV is empty; skip heatmap.")
        return

    pivot = (
        lag.groupby(["pair", "lag_months"])["spearman_r"]
        .mean()
        .unstack("lag_months")
        .sort_index()
    )
    fig, ax = plt.subplots(figsize=(8, 4.5))
    im = ax.imshow(pivot.values, aspect="auto", cmap="RdBu_r", vmin=-0.6, vmax=0.6)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=8)
    ax.set_xlabel("Lag (months)")
    ax.set_title("Mean Spearman r across districts (anomaly lags)")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.values[i, j]
            if np.isfinite(val):
                ax.text(
                    j, i, f"{val:.2f}", ha="center", va="center", fontsize=8
                )
    fig.colorbar(im, ax=ax, shrink=0.8, label="Spearman r")
    plt.tight_layout()
    out = os.path.join(_figures_dir(), "lag_correlations_heatmap.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.show()
    plt.close(fig)
    print("Saved:", out)


def plot_terra_aqua_gap():
    """Annual mean Terra − Aqua LST difference."""
    import matplotlib.pyplot as plt

    gap_path = os.path.join(ANALYSIS_DIR, "terra_aqua_annual_gap.csv")
    cons_path = os.path.join(ANALYSIS_DIR, "terra_aqua_consistency.csv")
    if not os.path.exists(gap_path):
        raise FileNotFoundError(f"Missing {gap_path}")
    gap = pd.read_csv(gap_path)

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(gap["year"], gap["terra_minus_aqua"], marker="o", lw=1.2)
    ax.axhline(0, color="gray", ls="--", lw=0.8)
    ax.set_title("Annual mean difference: Terra LST − Aqua LST (°C)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Terra − Aqua (°C)")
    ax.grid(True, ls=":", alpha=0.5)
    if os.path.exists(cons_path):
        cons = pd.read_csv(cons_path)
        if len(cons):
            r = cons.iloc[0].get("pearson_r", np.nan)
            mean_gap = cons.iloc[0].get("mean_terra_minus_aqua_c", np.nan)
            ax.text(
                0.02,
                0.95,
                f"r = {r:.3f}  |  mean gap = {mean_gap:.2f} °C",
                transform=ax.transAxes,
                va="top",
                fontsize=9,
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
            )
    plt.tight_layout()
    out = os.path.join(_figures_dir(), "terra_aqua_annual_gap.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.show()
    plt.close(fig)
    print("Saved:", out)


if RUN_PLOTS:
    print("\n==============================")
    print("GENERATING FIGURES")
    print("==============================")
    # Analysis-side imports needed if plots run without RUN_ANALYSIS
    if not RUN_ANALYSIS:
        from scipy import stats as sps  # noqa: F401 — used if cascade rebuilds
        ensure_project_dirs()
        EXPORT_DIR = os.path.abspath(EXPORT_DIR)
        ANALYSIS_DIR = os.path.abspath(ANALYSIS_DIR)
        SOURCE_DIR = os.path.abspath(SOURCE_DIR)
        FIGURES_DIR = os.path.abspath(FIGURES_DIR)
        DATA_DIR = EXPORT_DIR
    try:
        plot_canal_exposure_map()
    except Exception as exc:
        print("Canal map skipped:", exc)
    try:
        plot_drought_event_timelines()
    except Exception as exc:
        print("Event timelines skipped:", exc)
    try:
        plot_cascade_timeseries(PLOT_DISTRICT)
    except Exception as exc:
        print("Cascade timeseries skipped:", exc)
    try:
        plot_lag_heatmap()
    except Exception as exc:
        print("Lag heatmap skipped:", exc)
    try:
        plot_terra_aqua_gap()
    except Exception as exc:
        print("Terra–Aqua gap plot skipped:", exc)
    print("\nFigures directory:", _figures_dir())
    print("PLOTS COMPLETE")
