# Case Folder

This folder contains the Fluent case required to run the DPM RTD workflow.

## Contents

| File | Purpose |
| --- | --- |
| `dpm.cas.h5` | Fluent HDF5 case file used by the production journal |

No Fluent data file is required for the retained workflow because the journal
hybrid-initializes and advances the transient solution from the case file.

## Geometry And Zones

The case is a straight circular pipe:

| Item | Value |
| --- | --- |
| Length | `1.0 m` |
| Diameter | `0.0254 m` |
| Inlet zone | `inlet`, zone ID `6` |
| Outlet zone | `outlet`, zone ID `7` |
| Inlet location | `x = 1 m` |
| Outlet location | `x = 0 m` |

The coordinate direction matters. Fluid and DPM tracers travel from the inlet at
`x = 1 m` toward the outlet at `x = 0 m`, so the DPM injection velocity in the
journal is `u_x = -1 m/s`.

## Case Role In The Workflow

The case stores the mesh, cell zones, boundary zones, carrier-flow model setup,
and material definitions. The production journal adds the DPM pulse workflow at
runtime:

- hybrid initialization
- transient time-step setting
- pre-pulse carrier-flow advancement
- unsteady DPM tracking
- inlet surface pulse injection
- outlet DPM summary report

This keeps the repository small and avoids saving extra Fluent-generated data
files.

## Editing Guidance

- Keep this file name as `dpm.cas.h5` unless you also update
  `journals/run_rtd_dpm_fluent2023r2.jou` and any command examples.
- Save modified Fluent cases into this folder.
- Do not commit Fluent transcripts, cleanup batch files, `.phs`, `.dpm`, or
  report scratch files. They are ignored by the repository.
- If you change the geometry, inlet/outlet names, or flow direction, update the
  journal and README files because those details define the RTD interpretation.
