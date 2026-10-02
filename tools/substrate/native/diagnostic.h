// Bounded evidence for the two prospective MJPC adaptation diagnostics.
#pragma once
#include "diagnostic_budget.h"
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <filesystem>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
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

  void BeginCall(const mjpc::iLQGPlanner& p) {
    if (call_active_) throw std::runtime_error("planner summary call already active");
    pre_policy_ = Summarize(p.policy.trajectory);
    pre_previous_policy_ = Summarize(p.previous_policy.trajectory);
    pre_worker_warmstart_ = SummarizeWarmstarts(p);
    call_active_ = true;
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
      << ",\"mode\":\"" << mode_ << "\"";
    if (!call_active_) throw std::runtime_error("planner summary call missing");
    const TrajectorySummary post_policy = Summarize(p.policy.trajectory);
    const TrajectorySummary selected = Summarize(best);
    const std::vector<WarmstartSummary> post_worker_warmstart = SummarizeWarmstarts(p);
    output_ << ",\"planner_history\":{\"call_index\":" << calls_ << ",\"pre_policy\":";
    WriteSummary(output_, pre_policy_);
    output_ << ",\"pre_previous_policy\":";
    WriteSummary(output_, pre_previous_policy_);
    output_ << ",\"post_policy\":";
    WriteSummary(output_, post_policy);
    output_ << ",\"selected_trajectory\":";
    WriteSummary(output_, selected);
    output_ << ",\"worker_warmstart\":{\"pre\":";
    WriteWarmstarts(output_, pre_worker_warmstart_);
    output_ << ",\"post\":";
    WriteWarmstarts(output_, post_worker_warmstart);
    output_ << "}},\"states\":[";
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
    call_active_ = false;
  }

 private:
  struct WarmstartSummary {
    int worker = -1;
    bool finite = true;
    double norm = 0.0;
    double max_abs = 0.0;
    std::uint64_t hash = 14695981039346656037ULL;
  };

  struct TrajectorySummary {
    int horizon = 0;
    int dim_state = 0;
    int dim_action = 0;
    bool finite = true;
    bool return_finite = true;
    double total_return = 0.0;
    std::uint64_t hash = 14695981039346656037ULL;
  };

  static std::uint64_t HashBytes(const void* data, std::size_t size,
                                 std::uint64_t hash) {
    const auto* bytes = static_cast<const unsigned char*>(data);
    for (std::size_t i = 0; i < size; ++i) {
      hash ^= bytes[i];
      hash *= 1099511628211ULL;
    }
    return hash;
  }

  static TrajectorySummary Summarize(const mjpc::Trajectory& trajectory) {
    TrajectorySummary result;
    result.horizon = trajectory.horizon;
    result.dim_state = trajectory.dim_state;
    result.dim_action = trajectory.dim_action;
    result.return_finite = std::isfinite(trajectory.total_return);
    result.finite = result.return_finite;
    if (result.return_finite) {
      result.total_return = trajectory.total_return;
      result.hash = HashBytes(&trajectory.total_return, sizeof(double), result.hash);
    }
    auto add = [&result](const std::vector<double>& values) {
      const std::size_t size = values.size();
      result.hash = HashBytes(&size, sizeof(size), result.hash);
      if (!values.empty()) {
        result.hash = HashBytes(values.data(), values.size() * sizeof(double), result.hash);
      }
      for (double value : values) result.finite = result.finite && std::isfinite(value);
    };
    add(trajectory.states);
    add(trajectory.actions);
    add(trajectory.times);
    return result;
  }

  static std::vector<WarmstartSummary> SummarizeWarmstarts(
      const mjpc::iLQGPlanner& planner) {
    std::vector<WarmstartSummary> summaries;
    summaries.reserve(planner.data_.size());
    for (int worker = 0; worker < static_cast<int>(planner.data_.size()); ++worker) {
      const mjData* data = planner.data_[worker].get();
      if (!data) throw std::runtime_error("null planner worker mjData");
      WarmstartSummary summary;
      summary.worker = worker;
      double squared_norm = 0.0;
      for (int i = 0; i < planner.model->nv; ++i) {
        const double value = data->qacc_warmstart[i];
        if (!std::isfinite(value)) summary.finite = false;
        const double magnitude = std::abs(value);
        squared_norm += value * value;
        if (magnitude > summary.max_abs) summary.max_abs = magnitude;
      }
      summary.norm = std::sqrt(squared_norm);
      summary.hash = HashBytes(data->qacc_warmstart,
                               planner.model->nv * sizeof(double), summary.hash);
      summaries.push_back(summary);
    }
    return summaries;
  }

  static void WriteWarmstarts(std::ostream& out,
                              const std::vector<WarmstartSummary>& summaries) {
    out << '[';
    for (std::size_t i = 0; i < summaries.size(); ++i) {
      if (i) out << ',';
      const auto& item = summaries[i];
      out << "{\"worker\":" << item.worker
          << ",\"finite\":" << (item.finite ? "true" : "false")
          << ",\"norm\":" << item.norm << ",\"max_abs\":" << item.max_abs
          << ",\"fnv1a64\":\"" << std::hex << std::setw(16)
          << std::setfill('0') << item.hash << std::dec << "\"}";
    }
    out << ']';
  }

  static void WriteSummary(std::ostream& out, const TrajectorySummary& summary) {
    out << "{\"horizon\":" << summary.horizon
        << ",\"dim_state\":" << summary.dim_state
        << ",\"dim_action\":" << summary.dim_action
        << ",\"finite\":" << (summary.finite ? "true" : "false")
        << ",\"return_finite\":" << (summary.return_finite ? "true" : "false")
        << ",\"total_return\":" << summary.total_return
        << ",\"fnv1a64\":\"" << std::hex << std::setw(16)
        << std::setfill('0') << summary.hash << std::dec << "\"}";
  }

  PrivateBudget budget_;
  std::string mode_;
  std::ofstream output_;
  long long reserved_=0;
  int calls_=0;
  bool call_active_=false;
  TrajectorySummary pre_policy_;
  TrajectorySummary pre_previous_policy_;
  std::vector<WarmstartSummary> pre_worker_warmstart_;
};
