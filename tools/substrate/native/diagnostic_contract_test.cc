#include "diagnostic.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <unistd.h>
int main(int argc,char** argv) {
  if(argc!=3) return 2;
  char err[2048]={};
  for(const char* mode:{"original","fixed"}) {
    std::unique_ptr<mjModel,decltype(&mj_deleteModel)> m(
      mj_loadXML(argv[1],nullptr,err,sizeof(err)),mj_deleteModel);
    if(!m) return 3;
    for(int i=0;i<m->nu;++i) m->actuator_biastype[i]=mjBIAS_AFFINE;
    std::string trace="/tmp/go2-diagnostic-contract-"+std::to_string(getpid())+"-"+mode;
    Diagnostic diag(m.get(),mode,argv[2],trace.c_str());
    std::unique_ptr<mjData,decltype(&mj_deleteData)> d(mj_makeData(m.get()),mj_deleteData);
    mj_resetDataKeyframe(m.get(),d.get(),0);
    for(int i=0;i<m->nv;++i) d->qvel[i]=15;
    mj_fwdPosition(m.get(),d.get());
    mj_fwdVelocity(m.get(),d.get());
    mj_fwdActuation(m.get(),d.get());
    for(int i=0;i<m->nu;++i) {
      int j=m->actuator_trnid[2*i];
      double force=60*(d->ctrl[i]-d->qpos[m->jnt_qposadr[j]])-5*d->qvel[m->jnt_dofadr[j]];
      if(std::abs(force-d->actuator_force[i])>1e-9) return 4;
    }
    mjpc::iLQGPlanner p;
    for(int i=0;i<150;++i) diag.Reserve(m.get(),p,36);
    bool stopped=false;
    try {diag.Reserve(m.get(),p,36);} catch(const std::exception&) {stopped=true;}
    const int floor=mj_name2id(m.get(),mjOBJ_GEOM,"floor");
    if(!stopped || diag.reserved()!=614400 || diag.budget().rollout_steps ||
       diag.budget().fd_step_upper_bound || floor<0 ||
       m->geom_pos[3*floor+2]!=-0.01) return 5;
    for(int i=0;i<m->nu;++i) if(m->actuator_forcelimited[i]) return 6;
    std::filesystem::remove(trace);
  }
  std::unique_ptr<mjModel,decltype(&mj_deleteModel)> m(
    mj_loadXML(argv[1],nullptr,err,sizeof(err)),mj_deleteModel);
  if(!m) return 7;
  const std::string legacy_trace="/tmp/go2-diagnostic-contract-legacy-"+std::to_string(getpid());
  bool rejected=false;
  try { Diagnostic legacy(m.get(),"corrected",argv[2],legacy_trace.c_str()); }
  catch(const std::runtime_error&) { rejected=true; }
  if(!rejected || std::filesystem::exists(legacy_trace)) return 8;
  std::cout<<"mapping/PD clamp and budget boundary PASS; zero integrations/optimizer calls\n";
}
