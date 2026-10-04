#include <mujoco/mujoco.h>
#include <stdlib.h>
#include <string.h>
int calls=0;
void mjd_transitionFD(const mjModel* m,mjData* d,mjtNum eps,mjtByte centered,
                     mjtNum* A,mjtNum* B,mjtNum* C,mjtNum* D) {
  if (m->nv!=18 || eps!=1e-6 || centered!=0 || !A || B || C || D) abort();
  int zero=!strcmp(getenv("GO2_FD_WARMSTART_MODE"),"zero");
  for(int i=0;i<18;++i) if(d->qacc_warmstart[i]!=(zero?0.0:(double)(i+1))) abort();
  for(int i=0;i<19;++i) if(d->qpos[i]!=(double)(100+i)) abort();
  for(int i=0;i<18;++i) if(d->qvel[i]!=(double)(200+i)) abort();
  ++calls; *A=123.0;
}
