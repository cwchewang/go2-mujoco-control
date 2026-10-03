#include "diagnostic_budget.h"
#include <mujoco/mujoco.h>
extern "C" void __real_mj_step(const mjModel*,mjData*);
extern "C" void __wrap_mj_step(const mjModel* m,mjData* d) {
  if(active_private_budget) {
    ++active_private_budget->rollout_steps; active_private_budget->Check();
  }
  __real_mj_step(m,d);
}
extern "C" void __real_mjd_transitionFD(const mjModel*,mjData*,mjtNum,mjtByte,
                                      mjtNum*,mjtNum*,mjtNum*,mjtNum*);
extern "C" void __wrap_mjd_transitionFD(const mjModel* m,mjData* d,
    mjtNum eps,mjtByte centered,mjtNum* A,mjtNum* B,mjtNum* C,mjtNum* D) {
  if(active_private_budget) {
    if(m->nv!=18 || m->na!=0 || m->nu!=12 ||
       m->opt.integrator!=mjINT_EULER || centered || eps!=1e-6)
      std::abort();
    // MuJoCo3.3.6 mjd_stepFD: one base Euler step, at most one per
    // enabled qpos/qvel tangent component and per enabled control.
    long long upper=1 + ((A||C)?2*m->nv:0) + ((B||D)?m->nu:0);
    ++active_private_budget->fd_calls;
    active_private_budget->fd_step_upper_bound += upper;
    active_private_budget->Check();
  }
  __real_mjd_transitionFD(m,d,eps,centered,A,B,C,D);
}
