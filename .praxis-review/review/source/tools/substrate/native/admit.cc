// Offline iLQG admission on the unchanged shared Go2 physical model.
// No external plant loop, DDS, UI, or capability evaluator.
#include <cmath>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <mujoco/mujoco.h>
#include "mjpc/planners/ilqg/planner.h"
#include "mjpc/task.h"
#include "mjpc/threadpool.h"

class Go2Admission final : public mjpc::Task {
 public:
  std::string Name() const override { return "Go2 offline admission"; }
  std::string XmlPath() const override { return ""; }
  class ResidualImpl final : public mjpc::BaseResidualFn {
   public:
    explicit ResidualImpl(const Go2Admission* t) : BaseResidualFn(t) {}
    void Residual(const mjModel* m, const mjData* d, double* r) const override {
      int n = 0;
      r[n++] = d->qpos[2] - 0.27;
      // Quaternion-derived body upright axis versus world vertical.
      const double w=d->qpos[3],x=d->qpos[4],y=d->qpos[5],z=d->qpos[6];
      r[n++] = 2*(x*z+w*y); r[n++] = 2*(y*z-w*x);
      r[n++] = 1-2*(x*x+y*y)-1;
      for(int i=0;i<3;++i) r[n++] = d->qvel[i];
      for(int i=7;i<m->nq;++i) r[n++] = d->qpos[i]-m->key_qpos[i];
      for(int i=0;i<m->nu;++i) r[n++] = d->ctrl[i];
    }
  };
  Go2Admission() : residual_(this) {}
 protected:
  std::unique_ptr<mjpc::ResidualFn> ResidualLocked() const override {
    return std::make_unique<ResidualImpl>(this);
  }
  ResidualImpl* InternalResidual() override { return &residual_; }
 private:
  ResidualImpl residual_;
};

static Go2Admission* active_task = nullptr;
static void Sensor(const mjModel* model,mjData* data,int stage) {
  if(stage==mjSTAGE_ACC && active_task)
    active_task->Residual(model,data,data->sensordata);
}
int main(int argc,char** argv) {
  if(argc!=2) { std::cerr<<"usage: go2_mjpc_admit TASK_XML\n"; return 2; }
  if(mj_version()!=336) { std::cerr<<"requires MuJoCo 3.3.6\n"; return 2; }
  char error[1024]={};
  std::unique_ptr<mjModel,decltype(&mj_deleteModel)> m(mj_loadXML(argv[1],nullptr,error,sizeof(error)),mj_deleteModel);
  if(!m) { std::cerr<<error<<"\n"; return 2; }
  if(m->nu!=12 || m->nq!=19 || m->nv!=18 || m->nkey<1 ||
      mj_name2id(m.get(),mjOBJ_KEY,"home")!=0 || std::abs(m->opt.timestep-.002)>1e-12)
    return 2;
  std::unique_ptr<mjData,decltype(&mj_deleteData)> d(mj_makeData(m.get()),mj_deleteData);
  mj_resetDataKeyframe(m.get(),d.get(),0);
  const int dimensions[5]={1,3,3,12,12};
  if(m->nsensor<5 || m->nuser_sensor<4) return 2;
  for(int i=0;i<5;++i)
    if(m->sensor_type[i]!=mjSENS_USER || m->sensor_dim[i]!=dimensions[i]) return 2;
  Go2Admission task;
  task.Reset(m.get());
  active_task=&task; mjcb_sensor=Sensor;
  mj_forward(m.get(),d.get());
  mjpc::State state; state.Allocate(m.get()); state.Set(m.get(),d.get());
  mjpc::iLQGPlanner planner;
  planner.Initialize(m.get(),task); planner.Allocate(); planner.Reset(21);
  planner.SetState(state);
  mjpc::ThreadPool pool(2);
  planner.NominalTrajectory(21,pool);
  const double initial_cost=planner.candidate_policy[0].trajectory.total_return;
  planner.OptimizePolicy(21,pool);
  double action[12]={};
  planner.ActionFromPolicy(action,nullptr,d->time,false);
  const double cost=planner.BestTrajectory()->total_return;
  bool finite=std::isfinite(cost) && std::isfinite(initial_cost) &&
      !planner.BestTrajectory()->failure && planner.BestTrajectory()->horizon==21;
  for(int i=0;i<12;++i) finite &= std::isfinite(action[i]) &&
      action[i]>=m->actuator_ctrlrange[2*i]-1e-9 && action[i]<=m->actuator_ctrlrange[2*i+1]+1e-9;
  std::cout<<std::setprecision(17)<<"{\"backend\":\"MJPC iLQG\",\"scope\":\"offline_static_state\",\"mujoco\":\""<<mj_versionString()
    <<"\",\"planner\":"<<2<<",\"plant_time_s\":"<<d->time
    <<",\"initial_cost\":"<<initial_cost<<",\"rollout_failure\":"<<(planner.BestTrajectory()->failure?"true":"false")<<",\"horizon_steps\":21,\"cost\":"<<cost<<",\"finite_bounded\":"<<(finite?"true":"false")<<",\"torque\":[";
  for(int i=0;i<12;++i) std::cout<<(i?",":"")<<action[i];
  std::cout<<"]}\n";
  mjcb_sensor=nullptr; active_task=nullptr;
  return finite && d->time==0 ? 0 : 1;
}
