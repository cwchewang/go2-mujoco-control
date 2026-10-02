// Bounded evidence for the two prospective MJPC adaptation diagnostics.
#pragma once
#include "diagnostic_budget.h"
#include <fstream>
#include <iomanip>
#include <filesystem>
#include <memory>
#include <stdexcept>
#include <string>
#include <mujoco/mujoco.h>
#include "mjpc/planners/ilqg/planner.h"
#include "mjpc/utilities.h"

class Diagnostic {
 public:
  static constexpr long long kReserve = 4096;
  static constexpr long long kLimit = 614400;
  Diagnostic(mjModel* source, const char* mode, const char* canonical,
             const char* trace) : mode_(mode) {
    if ((mode_ != "original" && mode_ != "fixed") ||
        std::filesystem::exists(trace))
      throw std::runtime_error("invalid diagnostic mode/trace");
    char error[2048] = {};
    std::unique_ptr<mjModel, decltype(&mj_deleteModel)> plant(
        mj_loadXML(canonical, nullptr, error, sizeof(error)), mj_deleteModel);
    if (!plant || plant->nq != 19 || plant->nv != 18 || plant->nu != 12 ||
        source->na != 0 || source->nq != 19 || source->nv != 18 ||
        source->opt.integrator != mjINT_EULER ||
        mjpc::GetNumberOrDefault(10, source, "ilqg_num_rollouts") != 10 ||
        mjpc::GetNumberOrDefault(0, source, "derivative_skip") != 0)
      throw std::runtime_error("diagnostic configuration outside proved bound");
    const int sf = mj_name2id(source, mjOBJ_GEOM, "floor");
    const int pf = mj_name2id(plant.get(), mjOBJ_GEOM, "phase2_floor");
    if (sf < 0 || pf < 0 || source->geom_type[sf] != mjGEOM_PLANE ||
        plant->geom_type[pf] != mjGEOM_PLANE ||
        source->geom_pos[3*sf+2] != -0.01 || plant->geom_pos[3*pf+2] != 0)
      throw std::runtime_error("unproved diagnostic floor mapping");
    for (int i = 0; i < source->nu; ++i) {
      int sj = source->actuator_trnid[2*i];
      const char* name = mj_id2name(source, mjOBJ_JOINT, sj);
      int pj = mj_name2id(plant.get(), mjOBJ_JOINT, name);
      int pa = -1;
      for (int j = 0; j < plant->nu; ++j)
        if (plant->actuator_trnid[2*j] == pj) {
          if (pa >= 0) throw std::runtime_error("duplicate canonical actuator");
          pa = j;
        }
      if (pj < 0 || pa < 0 ||
          plant->actuator_gaintype[pa] != mjGAIN_FIXED ||
          plant->actuator_gainprm[mjNGAIN*pa] != 1 ||
          plant->actuator_biastype[pa] != mjBIAS_NONE ||
          !plant->actuator_ctrllimited[pa] ||
          source->actuator_forcelimited[i] ||
          source->actuator_gear[6*i] != 1 || plant->actuator_gear[6*pa] != 1)
        throw std::runtime_error("unproved diagnostic torque mapping");
    }
    output_.open(trace);
    if (!output_) throw std::runtime_error("diagnostic trace cannot be created");
    active_private_budget=&budget_;
  }

  void Reserve(const mjModel* m, const mjpc::iLQGPlanner& p, int horizon) {
    if (m->nv != 18 || m->nu != 12 || m->na != 0 ||
        m->opt.integrator != mjINT_EULER || horizon != 36 ||
        p.settings.fd_mode != 0 || p.settings.fd_tolerance != 1e-6 ||
        calls_ >= 150 || reserved_ > kLimit - kReserve)
      throw std::runtime_error("private integration budget/configuration stop");
    ++calls_;
    reserved_ += kReserve; // upper-bound reservation, never an actual step count
    budget_.reserved=reserved_;
  }

  long long reserved() const { return reserved_; }
  int calls() const { return calls_; }
  const PrivateBudget& budget() const { return budget_; }
  ~Diagnostic() { active_private_budget=nullptr; }

  void Record(mjModel* source, mjData* live, mjpc::iLQGPlanner& p,
              const mjpc::Trajectory& best, double time) {
    std::unique_ptr<mjModel, decltype(&mj_deleteModel)> copy(
        mj_copyModel(nullptr, source), mj_deleteModel);
    mjpc::MakeDifferentiable(copy.get());
    std::unique_ptr<mjData, decltype(&mj_deleteData)> d(
        mj_makeData(copy.get()), mj_deleteData);
    if (best.horizon != 36 || best.dim_state != 37 ||
        best.times[0] != time || p.BestRollout() < 0)
      throw std::runtime_error("diagnostic prediction identity mismatch");
    mju_copy(d->mocap_pos, live->mocap_pos, 3*source->nmocap);
    mju_copy(d->mocap_quat, live->mocap_quat, 4*source->nmocap);
    mju_copy(d->userdata, live->userdata, source->nuserdata);
    output_ << std::setprecision(17)
      << "{\"policy_id\":" << calls_ << ",\"candidate_id\":" << p.BestRollout()
      << ",\"anchor_time_s\":" << time
      << ",\"optimization_model_id\":\"" << mode_ << "-go2-soft-v1\""
      << ",\"contact_semantics\":\"selected_states_forward_reconstruction_smoothed_private_model\""
      << ",\"mode\":\"" << mode_ << "\",\"states\":[";
    for (int t=0; t<best.horizon; ++t) {
      if (t) output_ << ',';
      const double* state=best.states.data()+37*t;
      mju_copy(d->qpos,state,19); mju_copy(d->qvel,state+19,18);
      mju_copy(d->ctrl,best.actions.data()+12*t,12);
      d->time=best.times[t];
      mj_forward(copy.get(),d.get()); // no integration; live planner data untouched
      output_ << "{\"time_s\":" << d->time << ",\"qpos\":[";
      for(int j=0;j<19;++j) { if(j) output_<<','; output_<<state[j]; }
      output_ << "],\"qvel\":[";
      for(int j=0;j<18;++j) { if(j) output_<<','; output_<<state[19+j]; }
      output_ << "],\"nominal_position_action\":[";
      for(int j=0;j<12;++j) { if(j) output_<<','; output_<<best.actions[12*t+j]; }
      output_ << "],\"active_contacts\":[";
      bool comma=false;
      for(int j=0;j<d->ncon;++j) if(d->contact[j].efc_address>=0) {
        if(comma) output_<<','; comma=true;
        const auto& c=d->contact[j];
        const char* a=mj_id2name(copy.get(),mjOBJ_GEOM,c.geom1);
        const char* b=mj_id2name(copy.get(),mjOBJ_GEOM,c.geom2);
        output_ << "{\"geom_ids\":["<<c.geom1<<','<<c.geom2
          <<"],\"geom_names\":[\""<<(a?a:"")<<"\",\""<<(b?b:"")
          <<"\"],\"distance_m\":"<<c.dist<<'}';
      }
      output_<<"]}";
    }
    output_ << "],\"private_accounting\":{\"rollout_mj_step_count\":"
      << budget_.rollout_steps.load()
      << ",\"fd_step_upper_bound_count\":"<<budget_.fd_step_upper_bound.load()
      << ",\"fd_call_count\":"<<budget_.fd_calls.load()
      << ",\"reserved_step_upper_bound\":"<<reserved_<<"}}\n"; output_.flush();
    if (!output_) throw std::runtime_error("diagnostic evidence write failure");
  }

 private:
  PrivateBudget budget_;
  std::string mode_;
  std::ofstream output_;
  long long reserved_=0;
  int calls_=0;
};
