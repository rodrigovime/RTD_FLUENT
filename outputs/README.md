# Outputs Folder

This folder contains the retained example artifacts from the Fluent DPM RTD
workflow.

## Contents

| File | Meaning |
| --- | --- |
| `dpm_summary.txt` | Fluent 2023 R2 DPM summary values used to build the example RTD artifacts |
| `rtd_curve.csv` | Binned RTD curve from the DPM-summary beta fit |
| `rtd_curve.png` | Plot of the fitted RTD curve |
| `rtd_fitted_parcel_times.csv` | Fitted parcel residence times used to construct the example histogram |
| `dpm_vectors.gif` | Schematic animation of the DPM pulse and carrier-flow vectors |

## Important Interpretation

The current Fluent batch run reported all DPM parcels escaping through the
outlet, with a mean residence time of `0.8677 s`. The raw transient DPM sample
file remained header-only in the batch workflow, so these example artifacts are
not raw sampled particle rows.

The RTD files in this folder are produced by
`tools/make_rtd_summary_artifacts.py`, which fits a bounded beta distribution
to the Fluent DPM summary statistics:

- parcel count
- minimum residence time
- maximum residence time
- mean residence time
- residence-time standard deviation
- injected and escaped mass

For publication-quality RTD data, use the UDF workflow and save the raw sample
output. Then run `tools/rtd_from_dpm_sample.py` to create a raw-sample RTD.

## Regenerating These Files

From the repository root:

```powershell
python tools\make_rtd_summary_artifacts.py --case case\dpm.cas.h5 --output-dir outputs --bins 48
```

If a new Fluent run reports updated DPM statistics, pass them explicitly:

```powershell
python tools\make_rtd_summary_artifacts.py `
  --case case\dpm.cas.h5 `
  --output-dir outputs `
  --count 228 `
  --min-s 0.7277 `
  --max-s 1.353 `
  --mean-s 0.8677 `
  --std-s 0.1813 `
  --injected-mass-kg 2.0e-14 `
  --escaped-mass-kg 2.0e-14
```

## `rtd_curve.csv` Columns

| Column | Meaning |
| --- | --- |
| `time_s` | Bin-center residence time |
| `E_1_per_s` | Normalized RTD density |
| `F` | Cumulative RTD |
| `bin_weight` | Fitted parcel count in the bin |
| `source` | Data provenance label |

The normalization is:

```math
\sum_j E_j \Delta t_j = 1
```

within histogram discretization error.
