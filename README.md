# Fluent DPM Residence Time Distribution (RTD)

This repository contains a minimal ANSYS Fluent workflow for obtaining a
residence time distribution (RTD) curve from a discrete phase model (DPM)
tracer pulse in a straight pipe.

The case is intentionally small and publishable:

- one Fluent case file
- one Fluent 2023 R2 batch journal
- Python tools for RTD postprocessing and example figures
- an optional DPM output UDF for raw particle sampling
- example output artifacts from the current run

## Repository Layout

```text
.
|-- case/
|   |-- dpm.cas.h5
|   `-- README.md
|-- journals/
|   |-- run_rtd_dpm_fluent2023r2.jou
|   `-- README.md
|-- outputs/
|   |-- dpm_summary.txt
|   |-- dpm_vectors.gif
|   |-- rtd_curve.csv
|   |-- rtd_curve.png
|   |-- rtd_fitted_parcel_times.csv
|   `-- README.md
|-- tools/
|   |-- make_rtd_summary_artifacts.py
|   |-- rtd_from_dpm_sample.py
|   `-- README.md
|-- udf/
|   |-- rtd_dpm_output.c
|   `-- README.md
|-- .gitattributes
|-- .gitignore
|-- README.md
`-- requirements.txt
```

## Software Requirements

- ANSYS Fluent 2023 R2
- Python 3.10 or newer
- Python packages listed in `requirements.txt`

Install the Python dependencies from the repository root:

```powershell
python -m pip install -r requirements.txt
```

The Fluent journal was tested with:

```powershell
& 'C:\Program Files\ANSYS Inc\v232\fluent\ntbin\win64\fluent.exe' 3d -g -t4 -i journals\run_rtd_dpm_fluent2023r2.jou
```

Adjust the Fluent executable path if your ANSYS installation is in a different
location.

## Physical Case

The domain is a straight circular pipe:

| Quantity | Value |
| --- | --- |
| Pipe length | `1.0 m` |
| Pipe diameter | `0.0254 m` |
| Inlet zone | `inlet`, zone ID `6`, located at `x = 1 m` |
| Outlet zone | `outlet`, zone ID `7`, located at `x = 0 m` |
| Flow direction | negative `x` direction |
| Nominal inlet speed | `1 m/s` |
| Ideal plug-flow time | `L / U = 1 s` |

The original Fluent case includes a transient carrier-flow setup with species
transport for air and ozone. The DPM RTD workflow uses small inert particles as
the tracer pulse. In this workflow the particles are used to measure residence
time; they are not intended to represent a finite-loading particulate process.

## Governing Equations

### Carrier Phase

For the incompressible carrier phase, Fluent solves the continuity equation:

```math
\nabla \cdot \mathbf{u} = 0
```

and the transient Reynolds-averaged momentum equation:

```math
\frac{\partial (\rho \mathbf{u})}{\partial t}
+ \nabla \cdot (\rho \mathbf{u}\mathbf{u})
=
-\nabla p
+ \nabla \cdot
\left[
  \mu_{\mathrm{eff}}
  \left(
    \nabla \mathbf{u} + \nabla \mathbf{u}^{T}
  \right)
\right]
```

where:

- `rho` is the carrier-fluid density
- `u` is the mean velocity vector
- `p` is pressure
- `mu_eff = mu + mu_t` is the molecular plus turbulent effective viscosity

The saved case contains turbulence variables `k` and `omega`, so it is
consistent with a `k-omega` RANS-style turbulence closure in Fluent.

If species transport is used, the passive scalar/species equation has the form:

```math
\frac{\partial (\rho Y_i)}{\partial t}
+ \nabla \cdot (\rho \mathbf{u}Y_i)
=
\nabla \cdot
\left[
  \rho D_{i,\mathrm{eff}} \nabla Y_i
\right]
+ S_i
```

The DPM RTD workflow does not require the ozone outlet monitor; it uses particle
escape residence times.

### Discrete Phase Tracer

Each DPM parcel follows:

```math
\frac{d\mathbf{x}_p}{dt} = \mathbf{u}_p
```

```math
\frac{d\mathbf{u}_p}{dt}
= F_D(\mathbf{u} - \mathbf{u}_p)
+ \frac{\mathbf{g}(\rho_p - \rho)}{\rho_p}
+ \mathbf{F}_{\mathrm{other}}
```

The drag acceleration coefficient used by Fluent can be written generally as:

```math
F_D =
\frac{18\mu}{\rho_p d_p^2}
\frac{C_D Re_p}{24}
```

with:

```math
Re_p = \frac{\rho d_p |\mathbf{u} - \mathbf{u}_p|}{\mu}
```

For this RTD run the DPM parcels are `1e-6 m` inert tracer particles injected
as a short pulse. Continuous-phase/discrete-phase coupling is kept off, so the
particles sample the carrier flow but do not alter it.

## Boundary Conditions

| Boundary | Carrier phase condition | DPM condition |
| --- | --- | --- |
| `inlet` | Velocity inlet, nominal speed `1 m/s` | Pulse injection on inlet surface |
| `outlet` | Pressure outlet | Escape boundary |
| Pipe wall | No-slip wall | Default wall behavior; particles in this run escaped at the outlet |

The inlet is geometrically located at `x = 1 m`; the flow points toward
`x = 0 m`. The production DPM journal therefore sets the injection velocity to:

```text
u_x = -1 m/s
u_y = 0 m/s
u_z = 0 m/s
```

## Initial Conditions and Time Advancement

The production journal applies this sequence:

1. Read `case/dpm.cas.h5`.
2. Hybrid-initialize the carrier flow.
3. Set the physical time step to `0.02 s`.
4. Run `100` time steps before the DPM pulse. This advances the carrier flow to
   `t = 2.0 s`.
5. Enable unsteady DPM tracking.
6. Create an inlet surface injection named `rtd-inlet`.
7. Inject the particle pulse from `t = 2.00 s` to `t = 2.02 s`.
8. Run `250` more time steps, ending at `t = 7.0 s`.
9. Print the Fluent DPM summary.

The extra run time after the pulse is long enough for all released parcels to
escape through the outlet in the current case.

## RTD Definitions

The RTD density `E(t)` is the normalized outlet response to a pulse input:

```math
E(t) = \frac{1}{M_0}\frac{dM_{\mathrm{out}}(t)}{dt}
```

where `M_0` is the total injected tracer amount that eventually exits through
the sampled outlet.

The cumulative distribution is:

```math
F(t) = \int_0^t E(\tau)\,d\tau
```

and the normalization condition is:

```math
\int_0^\infty E(t)\,dt = 1
```

The first two moments are:

```math
\bar{t} = \int_0^\infty tE(t)\,dt
```

```math
\sigma_t^2 =
\int_0^\infty (t - \bar{t})^2 E(t)\,dt
```

For discrete DPM outlet samples, each parcel or sample row has a residence time
`t_i` and a weight `w_i`. In a histogram bin `j` of width `Delta t_j`, the
normalized RTD estimate is:

```math
E_j =
\frac{\sum_{i \in j} w_i}
{\left(\sum_i w_i\right)\Delta t_j}
```

and the cumulative RTD is:

```math
F_j =
\frac{\sum_{k \leq j}\sum_{i \in k} w_i}
{\sum_i w_i}
```

## Current Fluent 2023 R2 Result

The retained example output came from the production journal in Fluent 2023 R2.
Fluent reported:

| Metric | Value |
| --- | --- |
| Escaped parcels | `228` |
| Residence time minimum | `0.7277 s` |
| Residence time maximum | `1.353 s` |
| Residence time mean | `0.8677 s` |
| Residence time standard deviation | `0.1813 s` |
| Injected DPM mass | `2.0e-14 kg` |
| Escaped DPM mass | `2.0e-14 kg` |

The Fluent batch run confirmed that all particles escaped through the outlet.
However, Fluent's transient DPM sample file remained header-only in this batch
workflow. For that reason, the example `outputs/rtd_curve.csv`,
`outputs/rtd_curve.png`, and `outputs/dpm_vectors.gif` are labeled as a bounded
beta fit to the Fluent DPM summary statistics, not as raw per-particle outlet
sample rows.

Use the optional UDF workflow in `udf/` when you need a raw sampled RTD for a
publication result.

## How To Reproduce The Example Output

From the repository root, run Fluent in batch mode:

```powershell
& 'C:\Program Files\ANSYS Inc\v232\fluent\ntbin\win64\fluent.exe' 3d -g -t4 -i journals\run_rtd_dpm_fluent2023r2.jou
```

Then regenerate the documented output artifacts:

```powershell
python tools\make_rtd_summary_artifacts.py --case case\dpm.cas.h5 --output-dir outputs --bins 48
```

The generated files are:

- `outputs/dpm_summary.txt`: the Fluent DPM summary values used by the fit
- `outputs/rtd_curve.csv`: binned `E(t)` and `F(t)` data
- `outputs/rtd_curve.png`: RTD plot
- `outputs/rtd_fitted_parcel_times.csv`: fitted parcel residence times used for
  the example histogram
- `outputs/dpm_vectors.gif`: schematic DPM pulse/vector animation

## How To Obtain A Raw DPM RTD

For a raw particle-sampled RTD instead of the summary-fit artifact:

1. Open `case/dpm.cas.h5` in Fluent 2023 R2.
2. Compile `udf/rtd_dpm_output.c`.
3. Hook `rtd_dpm_sample` as the output function for DPM sample trajectories.
4. Sample particles at the `outlet` surface.
5. Save the DPM sample output, for example as `outputs/rtd_sample.out`.
6. Convert it to a normalized RTD:

```powershell
python tools\rtd_from_dpm_sample.py outputs\rtd_sample.out --output outputs\rtd_curve_raw.csv --plot outputs\rtd_curve_raw.png --bins 80
```

The raw-sample converter writes:

- `time_s`: residence-time bin center
- `E_1_per_s`: normalized RTD density
- `F`: cumulative RTD
- `bin_weight`: parcel, mass, or row-count weight in the bin

## Notes For Publishing

- `.gitignore` excludes Fluent transcripts, cleanup scripts, temporary sample
  files, Python caches, and compiled UDF output.
- `.gitattributes` marks Fluent case files and image outputs as binary.
- Add a `LICENSE` file before public release if you want others to reuse the
  case or scripts under explicit terms.
- If you rerun the case and get different DPM summary values, pass the updated
  values to `tools/make_rtd_summary_artifacts.py` with `--mean-s`, `--std-s`,
  `--min-s`, `--max-s`, and related options.
