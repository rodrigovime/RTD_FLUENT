# UDF Folder

This folder contains the optional Fluent user-defined function for raw DPM RTD
sampling.

## Contents

| File | Purpose |
| --- | --- |
| `rtd_dpm_output.c` | `DEFINE_DPM_OUTPUT` function that writes particle residence-time data at a DPM sampling surface |

The Fluent batch journal can obtain a DPM summary without compiling this UDF.
Compile and hook the UDF when you need raw per-particle or per-parcel outlet
samples.

## What The UDF Writes

The output function writes one row per sampled DPM particle/parcel event with
these columns:

| Column | Meaning |
| --- | --- |
| `arrival_time_s` | Fluent particle time at the sample surface |
| `birth_time_s` | Particle injection time |
| `residence_time_s` | `arrival_time_s - birth_time_s` |
| `sample_weight` | Fluent parcel/sample weight |
| `parcel_mass_kg` | `sample_weight * particle_mass_kg` |
| `particle_mass_kg` | Single-particle mass |
| `diameter_m` | Particle diameter |
| `x_m`, `y_m`, `z_m` | Particle position |
| `u_m_s`, `v_m_s`, `w_m_s` | Particle velocity |
| `temperature_K` | Particle temperature |

The raw sample file can be converted with:

```powershell
python tools\rtd_from_dpm_sample.py outputs\rtd_sample.out --output outputs\rtd_curve_raw.csv --plot outputs\rtd_curve_raw.png --bins 80
```

## Fluent Hooking Workflow

In Fluent 2023 R2:

1. Open `case/dpm.cas.h5`.
2. Open `Define > User-Defined > Functions > Compiled`.
3. Add `udf/rtd_dpm_output.c`.
4. Build and load the compiled UDF library.
5. Configure the DPM pulse injection or run the production journal setup.
6. Open the DPM sample trajectories/report panel.
7. Select the `outlet` boundary as the sampling surface.
8. Select `rtd_dpm_sample` as the DPM output function.
9. Write the sample file, for example `outputs/rtd_sample.out`.
10. Run the transient DPM tracking long enough for the pulse to leave the pipe.

## Notes

- The UDF uses Fluent's parallel-safe `par_fprintf`/`par_fprintf_head` output
  functions.
- The first two `par_fprintf` arguments are sorting keys used internally by
  Fluent and are not part of the documented data payload.
- The postprocessor reads the last 14 numeric values from each line so it can
  tolerate Fluent-added sorting fields or formatting differences.
- Commit the source file, not Fluent's compiled `libudf/` directory.
