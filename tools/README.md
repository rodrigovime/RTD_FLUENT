# Tools Folder

This folder contains Python postprocessing tools for the RTD workflow.

## Contents

| File | Purpose |
| --- | --- |
| `make_rtd_summary_artifacts.py` | Builds example RTD CSV/PNG/GIF artifacts from Fluent DPM summary statistics |
| `rtd_from_dpm_sample.py` | Converts raw DPM sample rows from the UDF workflow into a normalized RTD curve |

Install dependencies from the repository root:

```powershell
python -m pip install -r requirements.txt
```

## `make_rtd_summary_artifacts.py`

Use this script after the Fluent batch journal when Fluent reports DPM escape
statistics but does not write raw transient DPM sample rows.

Default command:

```powershell
python tools\make_rtd_summary_artifacts.py --case case\dpm.cas.h5 --output-dir outputs --bins 48
```

Default summary values are embedded from the retained Fluent 2023 R2 run:

| Metric | Default |
| --- | --- |
| Escaped parcels | `228` |
| Min residence time | `0.7277 s` |
| Max residence time | `1.353 s` |
| Mean residence time | `0.8677 s` |
| Standard deviation | `0.1813 s` |
| Injected mass | `2.0e-14 kg` |
| Escaped mass | `2.0e-14 kg` |

Override those values when a new Fluent run reports different statistics:

```powershell
python tools\make_rtd_summary_artifacts.py `
  --case case\dpm.cas.h5 `
  --output-dir outputs `
  --bins 48 `
  --count 228 `
  --min-s 0.7277 `
  --max-s 1.353 `
  --mean-s 0.8677 `
  --std-s 0.1813 `
  --injected-mass-kg 2.0e-14 `
  --escaped-mass-kg 2.0e-14
```

Outputs:

- `dpm_summary.txt`
- `rtd_curve.csv`
- `rtd_curve.png`
- `rtd_fitted_parcel_times.csv`
- `dpm_vectors.gif`

Method:

1. Fit a bounded beta distribution over the reported residence-time interval.
2. Match the reported mean and standard deviation.
3. Generate fitted parcel quantiles.
4. Bin those fitted parcel times into `E(t)` and `F(t)`.
5. Draw the RTD plot.
6. Read inlet face centers from the Fluent HDF5 case and create a schematic DPM
   pulse/vector GIF.

This method is useful for documentation and quick visualization. It should be
labeled as a summary-statistics fit, not raw particle data.

## `rtd_from_dpm_sample.py`

Use this script when Fluent writes raw DPM sample output from
`udf/rtd_dpm_output.c`.

Example:

```powershell
python tools\rtd_from_dpm_sample.py outputs\rtd_sample.out --output outputs\rtd_curve_raw.csv --plot outputs\rtd_curve_raw.png --bins 80
```

CSV output columns:

| Column | Meaning |
| --- | --- |
| `time_s` | Residence-time bin center |
| `E_1_per_s` | Normalized RTD density |
| `F` | Cumulative RTD |
| `bin_weight` | Sum of sample weights in the bin |

Weighting modes:

| Option | Use |
| --- | --- |
| `--weight parcel` | Default. Uses Fluent parcel/sample weight when available |
| `--weight mass` | Uses parcel mass when particle mass varies |
| `--weight none` | Counts each sample row equally |

Use a fixed bin width instead of a fixed bin count:

```powershell
python tools\rtd_from_dpm_sample.py outputs\rtd_sample.out --output outputs\rtd_curve_raw.csv --bin-width 0.02
```

The script ignores comments, blank lines, and nonnumeric text. It reads the last
14 numeric values on each sample line, matching the UDF output payload.
