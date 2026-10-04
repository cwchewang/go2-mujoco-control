#include <mujoco/mujoco.h>
#include <string.h>
#include <stdlib.h>
extern int calls;
int main(void) {
 mjModel m={0};mjData d={0};m.nv=18;
 double warm[18],q[19],v[18],A=0.0;
 for(int i=0;i<18;++i){warm[i]=i+1;v[i]=200+i;}
 for(int i=0;i<19;++i)q[i]=100+i;
 d.qacc_warmstart=warm;d.qpos=q;d.qvel=v;
 mjd_transitionFD(&m,&d,1e-6,0,&A,NULL,NULL,NULL);
 return !(calls==1 && A==123.0);
}
