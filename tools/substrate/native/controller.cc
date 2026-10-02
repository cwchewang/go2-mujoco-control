#include "fresh_plan.h"
#include "diagnostic.h"
// Persistent headless controller for the pinned Go2 MJPC QuadrupedFlat+iLQG.
// It produces source-model position targets and never steps the evaluation plant.
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include <mujoco/mujoco.h>

#include "mjpc/planners/ilqg/planner.h"
#include "mjpc/states/state.h"
#include "mjpc/task.h"
#include "mjpc/tasks/quadruped/quadruped.h"
#include "mjpc/threadpool.h"
#include "mjpc/trajectory.h"
#include "mjpc/utilities.h"

namespace {
constexpr int kActuatorGearDim = 6;
mjpc::Task* g_task = nullptr;

void ResidualSensor(const mjModel* model, mjData* data, int stage) {
  if (g_task && stage == mjSTAGE_ACC) {
    g_task->Residual(model, data, data->sensordata);
  }
}

int SelectionParameterIndex(const mjModel* model, const std::string& target) {
  const std::string prefix = "residual_select_";
  int shift = 0;
  for (int i = 0; i < model->nnumeric; ++i) {
    const char* raw = mj_id2name(model, mjOBJ_NUMERIC, i);
    const std::string name = raw ? raw : "";
    if (name.rfind(prefix, 0) == 0) {
      if (name.substr(prefix.size()) == target) return shift;
      ++shift;
    }
  }
  return -1;
}

bool Finite(const std::vector<double>& values) {
  for (double value : values) {
    if (!std::isfinite(value)) return false;
  }
  return true;
}

int FeatureParameterIndex(const mjModel* model, const std::string& exact_name) {
  int shift = 0;
  for (int i = 0; i < model->nnumeric; ++i) {
    const char* raw = mj_id2name(model, mjOBJ_NUMERIC, i);
    if (!raw) continue;
    std::string name(raw);
    if (name.rfind("residual_", 0) != 0) continue;
    if (name == exact_name) return shift;
    ++shift;
  }
  return -1;
}

void MuJoCoWarningToStderr(const char* message) {
  std::cerr << "MUJOCO_WARNING: " << (message ? message : "") << std::endl;
}

void PrintError(const std::string& message) {
  std::cout << "{\"ok\":false,\"error\":\"";
  for (char c : message) {
    if (c == '"' || c == '\\') std::cout << '\\';
    std::cout << ((c == '\n' || c == '\r') ? ' ' : c);
  }
  std::cout << "\"";
  if(active_private_budget) std::cout << ",\"failed_private_accounting\":{"
    << "\"reserved_step_upper_bound\":"<<active_private_budget->reserved.load()
    << ",\"rollout_mj_step_count\":"<<active_private_budget->rollout_steps.load()
    << ",\"fd_step_upper_bound_count\":"<<active_private_budget->fd_step_upper_bound.load()
    << ",\"fd_call_count\":"<<active_private_budget->fd_calls.load()<<"}";
  std::cout << "}" << std::endl;
}

class Controller {
 public:
  explicit Controller(const char* task_xml, const char* diagnostic_mode=nullptr,
                      const char* canonical_xml=nullptr, const char* trace=nullptr)
      : model_(Load(task_xml), mj_deleteModel),
        data_(mj_makeData(model_.get()), mj_deleteData),
        pool_(4) {
    if (mj_version() != 336) throw std::runtime_error("requires MuJoCo 3.3.6");
    if (model_->nq != 19 || model_->nv != 18 || model_->nu != 12 ||
        model_->nkey < 1 || mj_name2id(model_.get(), mjOBJ_KEY, "home") != 0) {
      throw std::runtime_error("unexpected Go2 source model dimensions");
    }
    ValidateAndCorrectActuators();
    if (diagnostic_mode) diagnostic_=std::make_unique<Diagnostic>(
        model_.get(), diagnostic_mode, canonical_xml, trace);
    const char* transitions =
        mjpc::GetCustomTextData(model_.get(), "task_transition");
    if (!transitions ||
        std::string(transitions) != "Quadruped|Biped|Walk|Scramble|Flip") {
      throw std::runtime_error("unexpected QuadrupedFlat mode table");
    }

    planner_dt_ =
        mjpc::GetNumberOrDefault(0.01, model_.get(), "agent_timestep");
    const double horizon_s =
        mjpc::GetNumberOrDefault(0.35, model_.get(), "agent_horizon");
    if (!(planner_dt_ > 0) || !(horizon_s > 0)) {
      throw std::runtime_error("invalid source planner timing");
    }
    horizon_ = std::max(2, static_cast<int>(horizon_s / planner_dt_ + 1.0));
    model_->opt.timestep = planner_dt_;
    speed_index_ = mjpc::ParameterIndex(model_.get(), "Walk speed");
    turn_index_ = mjpc::ParameterIndex(model_.get(), "Walk turn");
    gait_switch_index_ = SelectionParameterIndex(model_.get(), "Gait switch");
    gait_index_ = SelectionParameterIndex(model_.get(), "Gait");
    manual_gait_switch_ = mjpc::ResidualParameterFromSelection(
        model_.get(), "Gait switch", "Manual");
    trot_gait_ =
        mjpc::ResidualParameterFromSelection(model_.get(), "Gait", "Trot");
    if (speed_index_ < 0 || turn_index_ < 0 || gait_switch_index_ < 0 ||
        gait_index_ < 0 ||
        mjpc::ResidualSelection(model_.get(), "Gait switch",
                                manual_gait_switch_) != "Manual" ||
        mjpc::ResidualSelection(model_.get(), "Gait", trot_gait_) != "Trot") {
      throw std::runtime_error("Walk command or gait parameters missing");
    }

    task_.Reset(model_.get());
    g_task = &task_;
    mjcb_sensor = ResidualSensor;
    state_.Allocate(model_.get());
    planner_.Initialize(model_.get(), task_);
    planner_.Allocate();
    SaveSolimp();
    Reset();

    std::cout << "{\"ready\":true,\"protocol\":3,\"nq\":19,\"nv\":18,\"nu\":12,"
              << "\"worker_count\":" << pool_.NumThreads()
              << ",\"planner\":\"MJPC iLQG\",\"planner_dt\":" << planner_dt_
              << ",\"horizon_steps\":" << horizon_
              << ",\"source_nominal_biastype\":\"mjBIAS_NONE\""
              << ",\"compatibility_correction\":\"private_model_mjBIAS_AFFINE\""
              << ",\"canonical_evaluation_plant_modified\":false"
              << ",\"gait_switch\":\"Manual\",\"gait\":\"Trot\""
              << ",\"ground_miss_handling\":\"rollout_warning_failure\""
              << ",\"warning_channel\":\"stderr\""
              << ",\"policy_freshness\":\"current_candidate_required\""
              << ",\"joint_names\":[";
    for (int i = 0; i < model_->nu; ++i) {
      if (i) std::cout << ',';
      int joint = model_->actuator_trnid[2 * i];
      const char* name = mj_id2name(model_.get(), mjOBJ_JOINT, joint);
      std::cout << '"' << (name ? name : "") << '"';
    }
    auto print_values = [](const char* name, const std::vector<double>& values) {
      std::cout << "],\"" << name << "\":[";
      for (int i = 0; i < static_cast<int>(values.size()); ++i) {
        if (i) std::cout << ',';
        std::cout << values[i];
      }
    };
    print_values("position_lower", position_lower_);
    print_values("position_upper", position_upper_);
    print_values("kp", kp_);
    print_values("kd", kd_);
    std::cout << "]}" << std::endl;
  }

  ~Controller() {
    mjcb_sensor = nullptr;
    g_task = nullptr;
  }

  void Reset() {
    task_.Reset(model_.get());
    mj_resetDataKeyframe(model_.get(), data_.get(), 0);
    mju_zero(data_->qvel, model_->nv);
    mj_forward(model_.get(), data_.get());
    planner_.Reset(mjpc::kMaxTrajectoryHorizon, data_->ctrl);
    state_.Reset();
    first_step_ = true;
    has_policy_ = false;
    planned_vx_ = 0;
    planned_wz_ = 0;
    last_time_ = -1;
    last_action_.assign(data_->ctrl, data_->ctrl + model_->nu);
  }

  void Step(bool replan, double time_s, double vx, double vy, double wz,
            const std::vector<double>& qpos,
            const std::vector<double>& qvel) {
    if (!std::isfinite(time_s) || time_s < 0 || !std::isfinite(vx) ||
        !std::isfinite(vy) || !std::isfinite(wz) || !Finite(qpos) ||
        !Finite(qvel)) {
      throw std::runtime_error("nonfinite controller input");
    }
    if (qpos.size() != 19 || qvel.size() != 18) {
      throw std::runtime_error("invalid state dimensions");
    }
    if (std::abs(vy) > 1e-12) {
      throw std::runtime_error(
          "QuadrupedFlat source has no lateral velocity command");
    }
    if (vx < 0 || vx > 4 || wz < -2 || wz > 2) {
      throw std::runtime_error("command outside source Walk envelope");
    }
    if (last_time_ >= 0 && time_s <= last_time_ + 1e-12) {
      throw std::runtime_error(
          "controller time must increase strictly; reset required");
    }
    if (!replan) {
      if (!has_policy_) {
        throw std::runtime_error("MJPC policy unavailable; replan required");
      }
      if (std::abs(vx - planned_vx_) > 1e-12 ||
          std::abs(wz - planned_wz_) > 1e-12) {
        throw std::runtime_error(
            "controller command changed outside a replan tick");
      }
    }

    mju_copy(data_->qpos, qpos.data(), model_->nq);
    mju_copy(data_->qvel, qvel.data(), model_->nv);
    mju_copy(data_->ctrl, last_action_.data(), model_->nu);
    data_->time = time_s;
    mj_forward(model_.get(), data_.get());

    if (first_step_) {
      // Fresh task state forces its first transition to Quadruped. Complete
      // that transition before requesting the validated Walk mode.
      task_.Transition(model_.get(), data_.get());
      first_step_ = false;
    }
    if (replan) {
      planned_vx_ = vx;
      planned_wz_ = wz;
    }
    task_.mode = 2;  // validated task_transition index: Walk
    task_.parameters[gait_switch_index_] = manual_gait_switch_;
    task_.parameters[gait_index_] = trot_gait_;
    task_.parameters[speed_index_] = planned_vx_;
    task_.parameters[turn_index_] = planned_wz_;
    task_.Transition(model_.get(), data_.get());

    state_.Set(model_.get(), data_.get());
    planner_.SetState(state_);

    long long planning_elapsed = 0;
    if (replan) {
      if (diagnostic_) diagnostic_->Reserve(model_.get(), planner_, horizon_);
      has_policy_ = false;
      InvalidateCurrentRollouts(planner_);
      MakePlanningModelDifferentiable();
      auto planning_start = std::chrono::steady_clock::now();
      try {
        planner_.OptimizePolicy(horizon_, pool_);
      } catch (...) {
        RestoreSolimp();
        throw;
      }
      planning_elapsed =
          std::chrono::duration_cast<std::chrono::microseconds>(
              std::chrono::steady_clock::now() - planning_start)
              .count();
      RestoreSolimp();
    }

    const mjpc::Trajectory* best =
        replan ? RequireFreshPlan(planner_, state_.state().data(),
                                  model_->nq + model_->nv + model_->na, time_s)
               : planner_.BestTrajectory();
    if (!best || best->failure || !std::isfinite(best->total_return)) {
      throw std::runtime_error("MJPC rollout failed");
    }
    if (replan) has_policy_ = true;
    std::vector<double> action(model_->nu, 0.0);
    const auto action_start = std::chrono::steady_clock::now();
    planner_.ActionFromPolicy(
        action.data(), state_.state().data(), state_.time(), false);
    const auto action_elapsed =
        std::chrono::duration_cast<std::chrono::microseconds>(
            std::chrono::steady_clock::now() - action_start)
            .count();
    for (int i = 0; i < model_->nu; ++i) {
      if (!std::isfinite(action[i]) ||
          action[i] < model_->actuator_ctrlrange[2 * i] - 1e-9 ||
          action[i] > model_->actuator_ctrlrange[2 * i + 1] + 1e-9) {
        throw std::runtime_error("MJPC action outside source actuator range");
      }
    }
    if (diagnostic_ && replan)
      diagnostic_->Record(model_.get(), data_.get(), planner_, *best, time_s);
    last_action_ = action;
    last_time_ = time_s;

    std::cout << std::setprecision(17)
              << "{\"ok\":true,\"time_s\":" << time_s
              << ",\"vx\":" << vx << ",\"wz\":" << wz
              << ",\"cost\":" << best->total_return
              << ",\"replanned\":" << (replan ? "true" : "false")
              << ",\"current_rollout_valid\":true"
              << ",\"planning_compute_us\":" << planning_elapsed
              << ",\"action_compute_us\":" << action_elapsed
              << ",\"q_des\":[";
    for (int i = 0; i < model_->nu; ++i) {
      if (i) std::cout << ',';
      std::cout << action[i];
    }
    std::cout << "]";
    if (diagnostic_) std::cout << ",\"diagnostic\":{\"policy_id\":"
      << diagnostic_->calls() << ",\"private_step_upper_bound_reserved\":"
      << diagnostic_->reserved() << ",\"private_step_limit\":"
      << Diagnostic::kLimit
      << ",\"rollout_mj_step_count\":"<<diagnostic_->budget().rollout_steps.load()
      << ",\"fd_step_upper_bound_count\":"<<diagnostic_->budget().fd_step_upper_bound.load()
      << ",\"fd_call_count\":"<<diagnostic_->budget().fd_calls.load()<<"}";
    std::cout << "}" << std::endl;
  }

 private:
  static mjModel* Load(const char* path) {
    char error[2048] = {};
    mjModel* model = mj_loadXML(path, nullptr, error, sizeof(error));
    if (!model) throw std::runtime_error(error);
    return model;
  }

  void ValidateAndCorrectActuators() {
    position_lower_.resize(model_->nu);
    position_upper_.resize(model_->nu);
    kp_.resize(model_->nu);
    kd_.resize(model_->nu);
    for (int i = 0; i < model_->nu; ++i) {
      const double gain = model_->actuator_gainprm[mjNGAIN * i];
      const double* bias = model_->actuator_biasprm + mjNBIAS * i;
      if (model_->actuator_trntype[i] != mjTRN_JOINT ||
          model_->actuator_gaintype[i] != mjGAIN_FIXED ||
          model_->actuator_biastype[i] != mjBIAS_NONE ||
          model_->actuator_dyntype[i] != mjDYN_NONE ||
          !model_->actuator_ctrllimited[i] ||
          model_->actuator_forcelimited[i] ||
          std::abs(gain - 60.0) > 1e-12 ||
          std::abs(bias[0]) > 1e-12 ||
          std::abs(bias[1] + 60.0) > 1e-12 ||
          std::abs(bias[2] + 5.0) > 1e-12) {
        throw std::runtime_error(
            "pinned source actuator semantics changed before compatibility correction");
      }
      for (int k = 1; k < mjNGAIN; ++k) {
        if (std::abs(model_->actuator_gainprm[mjNGAIN * i + k]) > 1e-12) {
          throw std::runtime_error("unexpected source gain parameters");
        }
      }
      for (int k = 3; k < mjNBIAS; ++k) {
        if (std::abs(bias[k]) > 1e-12) {
          throw std::runtime_error("unexpected source bias parameters");
        }
      }
      const double* gear = model_->actuator_gear + kActuatorGearDim * i;
      if (std::abs(gear[0] - 1) > 1e-12) {
        throw std::runtime_error("non-unit source actuator gear");
      }
      for (int k = 1; k < kActuatorGearDim; ++k) {
        if (std::abs(gear[k]) > 1e-12) {
          throw std::runtime_error("non-unit source actuator gear");
        }
      }
      int joint = model_->actuator_trnid[2 * i];
      if (model_->jnt_type[joint] != mjJNT_HINGE ||
          model_->jnt_actfrclimited[joint]) {
        throw std::runtime_error("unsupported source joint transmission");
      }
      const double lo = model_->actuator_ctrlrange[2 * i];
      const double hi = model_->actuator_ctrlrange[2 * i + 1];
      if (!std::isfinite(lo) || !std::isfinite(hi) || !(lo < hi)) {
        throw std::runtime_error("invalid source position target range");
      }
      position_lower_[i] = lo;
      position_upper_[i] = hi;
      kp_[i] = gain;
      kd_[i] = -bias[2];
    }
    // Compatibility correction is confined to this controller's private model.
    // The canonical evaluation plant is never touched.
    for (int i = 0; i < model_->nu; ++i) {
      model_->actuator_biastype[i] = mjBIAS_AFFINE;
    }
  }

  void SaveSolimp() {
    jnt_solimp_.resize(model_->njnt);
    geom_solimp_.resize(model_->ngeom);
    pair_solimp_.resize(model_->npair);
    for (int i = 0; i < model_->njnt; ++i) {
      jnt_solimp_[i] = model_->jnt_solimp[mjNIMP * i];
    }
    for (int i = 0; i < model_->ngeom; ++i) {
      geom_solimp_[i] = model_->geom_solimp[mjNIMP * i];
    }
    for (int i = 0; i < model_->npair; ++i) {
      pair_solimp_[i] = model_->pair_solimp[mjNIMP * i];
    }
  }

  void MakePlanningModelDifferentiable() {
    RestoreSolimp();
    mjpc::MakeDifferentiable(model_.get());
  }

  void RestoreSolimp() {
    for (int i = 0; i < model_->njnt; ++i) {
      model_->jnt_solimp[mjNIMP * i] = jnt_solimp_[i];
    }
    for (int i = 0; i < model_->ngeom; ++i) {
      model_->geom_solimp[mjNIMP * i] = geom_solimp_[i];
    }
    for (int i = 0; i < model_->npair; ++i) {
      model_->pair_solimp[mjNIMP * i] = pair_solimp_[i];
    }
  }

  std::unique_ptr<mjModel, decltype(&mj_deleteModel)> model_;
  std::unique_ptr<mjData, decltype(&mj_deleteData)> data_;
  std::unique_ptr<Diagnostic> diagnostic_;
  mjpc::QuadrupedFlat task_;
  mjpc::State state_;
  mjpc::iLQGPlanner planner_;
  mjpc::ThreadPool pool_;
  int horizon_ = 0;
  double planner_dt_ = 0;
  int speed_index_ = -1;
  int turn_index_ = -1;
  int gait_switch_index_ = -1;
  int gait_index_ = -1;
  double manual_gait_switch_ = 0;
  double trot_gait_ = 0;
  bool first_step_ = true;
  bool has_policy_ = false;
  double planned_vx_ = 0;
  double planned_wz_ = 0;
  double last_time_ = -1;
  std::vector<double> last_action_;
  std::vector<double> position_lower_;
  std::vector<double> position_upper_;
  std::vector<double> kp_;
  std::vector<double> kd_;
  std::vector<double> jnt_solimp_;
  std::vector<double> geom_solimp_;
  std::vector<double> pair_solimp_;
};

std::vector<double> ReadVector(std::istringstream& stream, int size) {
  std::vector<double> values(size);
  for (double& value : values) {
    if (!(stream >> value)) throw std::runtime_error("truncated step packet");
  }
  return values;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc != 2 && argc != 5) {
    std::cerr << "usage: go2_mjpc_controller TASK_XML\n";
    return 2;
  }
  mju_user_warning = MuJoCoWarningToStderr;
  try {
    Controller controller(argv[1], argc==5 ? argv[2] : nullptr,
                          argc==5 ? argv[3] : nullptr,
                          argc==5 ? argv[4] : nullptr);
    std::string line;
    while (std::getline(std::cin, line)) {
      try {
        std::istringstream stream(line);
        std::string operation;
        if (!(stream >> operation)) continue;
        if (operation == "quit") return 0;
        if (operation == "reset") {
          controller.Reset();
          std::cout << "{\"ok\":true,\"reset\":true}" << std::endl;
          continue;
        }
        if (operation != "step") throw std::runtime_error("unknown operation");
        int replan_flag;
        double time_s, vx, vy, wz;
        if (!(stream >> replan_flag >> time_s >> vx >> vy >> wz)) {
          throw std::runtime_error("truncated step header");
        }
        if (replan_flag != 0 && replan_flag != 1) {
          throw std::runtime_error("invalid replan flag");
        }
        auto qpos = ReadVector(stream, 19);
        auto qvel = ReadVector(stream, 18);
        std::string extra;
        if (stream >> extra) throw std::runtime_error("extra step fields");
        controller.Step(replan_flag == 1, time_s, vx, vy, wz, qpos, qvel);
      } catch (const std::exception& error) {
        PrintError(error.what());
      }
    }
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 2;
  }
  return 0;
}
