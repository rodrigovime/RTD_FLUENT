# Journals Folder

This folder contains the Fluent batch journal that reproduces the DPM RTD run.

## Contents

| File | Purpose |
| --- | --- |
| `run_rtd_dpm_fluent2023r2.jou` | Production Fluent 2023 R2 journal for the DPM pulse RTD workflow |

All exploratory probe journals were removed from the publishable repository.

## Running The Journal

From the repository root:

```powershell
& 'C:\Program Files\ANSYS Inc\v232\fluent\ntbin\win64\fluent.exe' 3d -g -t4 -i journals\run_rtd_dpm_fluent2023r2.jou
```

Arguments:

- `3d`: open Fluent in 3D mode
- `-g`: run without the graphical interface
- `-t4`: use four solver processes
- `-i`: read and execute the journal file

## Journal Sequence

The journal performs the following operations:

1. Read `case/dpm.cas.h5`.
2. Hybrid-initialize the solution.
3. Set physical time step to `0.02 s`.
4. Advance `100` time steps before injecting particles.
5. Enable unsteady DPM tracking.
6. Set DPM tracking controls.
7. Create surface injection `rtd-inlet` on zone `inlet`.
8. Inject a short pulse from `t = 2.00 s` to `t = 2.02 s`.
9. Sample/report DPM behavior at the outlet.
10. Advance `250` additional time steps.
11. Print the DPM summary.
12. Exit Fluent.

## Important Parameters

| Parameter | Value | Meaning |
| --- | --- | --- |
| Time step | `0.02 s` | Physical transient time step |
| Pre-pulse steps | `100` | Develops carrier flow to `t = 2.0 s` |
| Post-pulse steps | `250` | Runs to `t = 7.0 s` |
| Injection name | `rtd-inlet` | DPM pulse identifier |
| Injection surface | `inlet` | Particle release boundary |
| Injection velocity | `(-1, 0, 0) m/s` | Flow direction from `x = 1` to `x = 0` |
| Particle diameter | `1e-6 m` | Small inert tracer particle |
| Pulse start | `2.00 s` | Start of particle release |
| Pulse stop | `2.02 s` | End of particle release |
| Injection mass flow | `1e-12 kg/s` | DPM parcel source strength |

## Editing The Journal

Common edits:

- Change `-t4` in the command line, not the journal, if you want a different
  number of Fluent processes.
- Change the read-case path if the case file is renamed.
- Change pulse timing if the carrier flow needs a longer pre-run.
- Change particle diameter or injection mass flow if the DPM tracer assumptions
  are changed.
- Keep the outlet DPM boundary as `escape` for RTD work.

If the inlet or outlet zone names are changed in Fluent, update the journal
prompts that reference `inlet` and `outlet`.
