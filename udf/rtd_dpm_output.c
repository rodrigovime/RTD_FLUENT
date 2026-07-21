#include "udf.h"

/*
 * DPM sampling output for residence-time distribution (RTD) work.
 *
 * Hook this function in the DPM Sample Trajectories dialog and sample the
 * outlet boundary. The output columns are intentionally simple whitespace
 * separated numbers so tools/rtd_from_dpm_sample.py can process them.
 */

DEFINE_DPM_OUTPUT(rtd_dpm_sample, header, fp, tp, thread, plane)
{
  if (header)
  {
    par_fprintf_head(fp,
      "# arrival_time_s birth_time_s residence_time_s sample_weight "
      "parcel_mass_kg particle_mass_kg diameter_m x_m y_m z_m "
      "u_m_s v_m_s w_m_s temperature_K\n");
    return;
  }

  if (NULLP(tp))
    return;

  {
    real arrival_time = TP_TIME(tp);
    real birth_time = TP_TIME_OF_BIRTH(tp);
    real residence_time = arrival_time - birth_time;
    real particle_mass = 0.0;
    real sample_weight = 1.0;
    real parcel_mass = 0.0;

    if (TP_INJECTION(tp)->type != DPM_TYPE_MASSLESS)
    {
      particle_mass = TP_MASS(tp);

      if (dpm_par.unsteady_tracking)
      {
        sample_weight = TP_N(tp);
      }
      else
      {
        sample_weight = TP_INIT_MASS(tp) > 0.0
          ? TP_FLOW_RATE(tp) / TP_INIT_MASS(tp)
          : 1.0;
        if (TP_STOCHASTIC(tp))
          sample_weight /= (real)TP_STOCHASTIC_NTRIES(tp);
      }

      parcel_mass = sample_weight * particle_mass;
    }

    /*
     * Fluent uses the first two par_fprintf arguments internally for sorting;
     * they are not written as output columns.
     */
    par_fprintf(fp,
      "%d %" int64_fmt
      " %.12e %.12e %.12e %.12e %.12e %.12e %.12e"
      " %.12e %.12e %.12e %.12e %.12e %.12e\n",
      P_INJ_ID(TP_INJECTION(tp)),
      TP_ID(tp),
      arrival_time,
      birth_time,
      residence_time,
      sample_weight,
      parcel_mass,
      particle_mass,
      TP_DIAM(tp),
      TP_POS(tp)[0],
      TP_POS(tp)[1],
      TP_POS(tp)[2],
      TP_VEL(tp)[0],
      TP_VEL(tp)[1],
      TP_VEL(tp)[2],
      TP_T(tp));
  }
}
