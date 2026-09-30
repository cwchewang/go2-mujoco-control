// Bounded, GUI-free engineering admission for the pinned MJPC Go2 Agent.
// This executable uses only ephemeral model copies; it does not edit the
// upstream XML or the project's canonical evaluation plant.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include <mujoco/mujoco.h>
#include "mjpc/agent.h"
#include "mjpc/tasks/quadruped/quadruped.h"

#ifndef GO2_MJPC_SOURCE_COMMIT
#error "CMake must bind the comparator binary to the verified MJPC commit"
#endif
#ifndef GO2_CXX_COMPILER_ID
#error "CMake must expose compiler identity in the comparator binary"
#endif
#ifndef GO2_CXX_COMPILER_VERSION
#error "CMake must expose compiler version in the comparator binary"
#endif

namespace {

using ModelPtr = std::unique_ptr<mjModel, decltype(&mj_deleteModel)>;
using DataPtr = std::unique_ptr<mjData, decltype(&mj_deleteData)>;

constexpr int kActuatorCount = 12;
constexpr int kHomeHoldSteps = 500;       // 1.0 s at the pinned 2 ms plant step.
constexpr int kProbeControlUpdates = 50;  // 0.5 s at the task's 10 ms Agent step.
constexpr double kExpectedPlantStep = 0.002;
constexpr double kExpectedAgentStep = 0.01;

void Require(bool condition, const std::string& message) {
  if (!condition) throw std::runtime_error(message);
}

bool StateFinite(const mjModel* model, const mjData* data) {
  for (int i = 0; i < model->nq; ++i) {
    if (!std::isfinite(data->qpos[i])) return false;
  }
  for (int i = 0; i < model->nv; ++i) {
    if (!std::isfinite(data->qvel[i]) || !std::isfinite(data->qacc[i])) {
      return false;
    }
  }
  for (int i = 0; i < model->nu; ++i) {
    if (!std::isfinite(data->ctrl[i]) ||
        !std::isfinite(data->actuator_force[i])) {
      return false;
    }
  }
  for (int i = 0; i < 3 * model->nbody; ++i) {
    if (!std::isfinite(data->xpos[i])) return false;
  }
  return std::isfinite(data->time);
}

double MaxAbs(const std::vector<double>& values) {
  double maximum = 0.0;
  for (double value : values) maximum = std::max(maximum, std::abs(value));
  return maximum;
}

struct HoldResult {
  double uncorrected_force_max = 0.0;
  double corrected_force_max = 0.0;
  double min_height = 0.0;
  double max_height = 0.0;
  double xy_displacement = 0.0;
  double max_joint_error = 0.0;
  double simulated_seconds = 0.0;
  bool finite = true;
  bool passed = false;
};

HoldResult RunHomeHold(const mjModel* nominal, const mjModel* corrected) {
  HoldResult result;
  const int trunk = mj_name2id(corrected, mjOBJ_BODY, "trunk");
  Require(trunk >= 0, "trunk body missing from pinned QuadrupedFlat model");

  DataPtr nominal_data(mj_makeData(nominal), mj_deleteData);
  DataPtr data(mj_makeData(corrected), mj_deleteData);
  Require(nominal_data && data, "MuJoCo could not allocate home-hold data");
  const int home = mj_name2id(corrected, mjOBJ_KEY, "home");
  Require(home == 0, "pinned home keyframe identity changed");
  mj_resetDataKeyframe(nominal, nominal_data.get(), home);
  mj_forward(nominal, nominal_data.get());
  mj_resetDataKeyframe(corrected, data.get(), home);
  mj_forward(corrected, data.get());

  // At the keyframe, ctrl equals the desired joint position and qvel is zero.
  // With the source biastype, only gain*ctrl is active. With affine bias, the
  // validated 60*ctrl - 60*q - 5*qvel law returns zero at that same setpoint.
  for (int actuator = 0; actuator < corrected->nu; ++actuator) {
    result.uncorrected_force_max = std::max(
        result.uncorrected_force_max,
        std::abs(nominal_data->actuator_force[actuator]));
    result.corrected_force_max = std::max(
        result.corrected_force_max,
        std::abs(data->actuator_force[actuator]));
  }
  Require(result.uncorrected_force_max > 1.0,
          "nominal non-affine model no longer exposes the expected bias omission");
  Require(result.corrected_force_max < 1.0e-8,
          "affine correction did not restore zero PD force at the home setpoint");

  std::vector<double> home_ctrl(corrected->nu);
  std::copy(data->ctrl, data->ctrl + corrected->nu, home_ctrl.begin());
  const double x0 = data->xpos[3 * trunk];
  const double y0 = data->xpos[3 * trunk + 1];
  result.min_height = result.max_height = data->xpos[3 * trunk + 2];
  for (int step = 0; step < kHomeHoldSteps; ++step) {
    std::copy(home_ctrl.begin(), home_ctrl.end(), data->ctrl);
    mj_step(corrected, data.get());
    result.finite = result.finite && StateFinite(corrected, data.get());
    const double height = data->xpos[3 * trunk + 2];
    result.min_height = std::min(result.min_height, height);
    result.max_height = std::max(result.max_height, height);
    const double dx = data->xpos[3 * trunk] - x0;
    const double dy = data->xpos[3 * trunk + 1] - y0;
    result.xy_displacement = std::max(result.xy_displacement, std::hypot(dx, dy));
    for (int q = 7; q < corrected->nq; ++q) {
      result.max_joint_error = std::max(
          result.max_joint_error,
          std::abs(data->qpos[q] - corrected->key_qpos[corrected->nq * home + q]));
    }
  }
  result.simulated_seconds = data->time;
  result.passed = result.finite && result.min_height >= 0.15 &&
                  result.xy_displacement <= 0.10 &&
                  result.max_joint_error <= 0.35;
  return result;
}

struct ProbeResult {
  int planning_updates = 0;
  int plant_steps = 0;
  double simulated_seconds = 0.0;
  double wall_seconds = 0.0;
  double planning_wall_seconds = 0.0;
  double height_initial = 0.0;
  double height_min = 0.0;
  double height_max = 0.0;
  double height_final = 0.0;
  double displacement_x = 0.0;
  double displacement_y = 0.0;
  double displacement_xy = 0.0;
  double plan_time_p50_ms = 0.0;
  double plan_time_p95_ms = 0.0;
  double plan_time_max_ms = 0.0;
  bool finite = true;
  bool mode_walk = false;
};

double Percentile(std::vector<double> values, double fraction) {
  if (values.empty()) return 0.0;
  std::sort(values.begin(), values.end());
  const std::size_t index = static_cast<std::size_t>(
      std::ceil(fraction * static_cast<double>(values.size())) - 1.0);
  return values[std::min(index, values.size() - 1)];
}

ProbeResult RunAgentProbe(const mjModel* model) {
  ProbeResult result;
  const int trunk = mj_name2id(model, mjOBJ_BODY, "trunk");
  Require(trunk >= 0, "trunk body missing from pinned QuadrupedFlat model");
  const int agent_step_id = mj_name2id(model, mjOBJ_NUMERIC, "agent_timestep");
  Require(agent_step_id >= 0, "agent_timestep missing from task_flat.xml");
  const double agent_step =
      model->numeric_data[model->numeric_adr[agent_step_id]];
  Require(std::abs(agent_step - kExpectedAgentStep) < 1.0e-12,
          "task_flat.xml Agent timestep differs from the admitted value");
  const double plant_step = model->opt.timestep;
  Require(std::abs(plant_step - kExpectedPlantStep) < 1.0e-12,
          "task_flat.xml plant timestep differs from the admitted value");
  const int substeps = static_cast<int>(std::llround(agent_step / plant_step));
  Require(substeps > 0 &&
              std::abs(substeps * plant_step - agent_step) < 1.0e-12,
          "Agent and plant timesteps do not have an integer ratio");

  auto task = std::make_shared<mjpc::QuadrupedFlat>();
  mjpc::Agent agent(model, task);
  DataPtr data(mj_makeData(model), mj_deleteData);
  Require(data != nullptr, "MuJoCo could not allocate Agent probe data");
  const int home = mj_name2id(model, mjOBJ_KEY, "home");
  mj_resetDataKeyframe(model, data.get(), home);
  mj_forward(model, data.get());

  Require(agent.SetModeByName("Quadruped") >= 0,
          "upstream Quadruped mode is missing");
  agent.ActiveTask()->Transition(const_cast<mjModel*>(model), data.get());
  Require(agent.SetSelectionParamByName("Gait switch", "Manual") >= 0,
          "upstream Manual gait-switch selection is missing");
  Require(agent.SetSelectionParamByName("Gait", "Trot") >= 0,
          "upstream Trot selection is missing");
  Require(agent.SetParamByName("Walk speed", 1.0) >= 0,
          "upstream Walk speed parameter is missing");
  Require(agent.SetParamByName("Walk turn", 0.0) >= 0,
          "upstream Walk turn parameter is missing");
  Require(agent.SetModeByName("Walk") >= 0,
          "upstream Walk mode is missing");
  agent.ActiveTask()->Transition(const_cast<mjModel*>(model), data.get());
  agent.plan_enabled = 1;

  result.mode_walk = agent.GetModeName() == "Walk";
  result.height_initial = data->xpos[3 * trunk + 2];
  result.height_min = result.height_max = result.height_initial;
  const double x0 = data->xpos[3 * trunk];
  const double y0 = data->xpos[3 * trunk + 1];
  std::vector<double> plan_times_ms;
  plan_times_ms.reserve(kProbeControlUpdates);
  mjpc::ThreadPool pool(2);
  const auto probe_start = std::chrono::steady_clock::now();
  double planning_seconds = 0.0;

  for (int update = 0; update < kProbeControlUpdates; ++update) {
    agent.SetState(data.get());
    const auto plan_start = std::chrono::steady_clock::now();
    agent.PlanIteration(&pool);
    const double plan_elapsed = std::chrono::duration<double>(
                                    std::chrono::steady_clock::now() - plan_start)
                                    .count();
    planning_seconds += plan_elapsed;
    plan_times_ms.push_back(1000.0 * plan_elapsed);

    double action[kActuatorCount] = {};
    agent.ActivePlanner().ActionFromPolicy(action, nullptr, data->time, false);
    for (int actuator = 0; actuator < model->nu; ++actuator) {
      if (!std::isfinite(action[actuator]) ||
          action[actuator] < model->actuator_ctrlrange[2 * actuator] - 1.0e-9 ||
          action[actuator] > model->actuator_ctrlrange[2 * actuator + 1] + 1.0e-9) {
        result.finite = false;
      }
    }
    for (int substep = 0; substep < substeps; ++substep) {
      std::copy(action, action + model->nu, data->ctrl);
      mj_step(model, data.get());
      agent.ActiveTask()->Transition(const_cast<mjModel*>(model), data.get());
      result.finite = result.finite && StateFinite(model, data.get());
      const double height = data->xpos[3 * trunk + 2];
      result.height_min = std::min(result.height_min, height);
      result.height_max = std::max(result.height_max, height);
    }
    result.plant_steps += substeps;
    result.planning_updates += 1;
  }

  result.wall_seconds = std::chrono::duration<double>(
                            std::chrono::steady_clock::now() - probe_start)
                            .count();
  result.planning_wall_seconds = planning_seconds;
  result.simulated_seconds = data->time;
  result.height_final = data->xpos[3 * trunk + 2];
  result.displacement_x = data->xpos[3 * trunk] - x0;
  result.displacement_y = data->xpos[3 * trunk + 1] - y0;
  result.displacement_xy =
      std::hypot(result.displacement_x, result.displacement_y);
  result.plan_time_p50_ms = Percentile(plan_times_ms, 0.50);
  result.plan_time_p95_ms = Percentile(plan_times_ms, 0.95);
  result.plan_time_max_ms =
      plan_times_ms.empty() ? 0.0 : *std::max_element(plan_times_ms.begin(), plan_times_ms.end());
  return result;
}

}  // namespace

int main(int argc, char** argv) {
  try {
    Require(argc == 2, "usage: go2_mjpc_comparator_probe TASK_FLAT_XML");
    Require(mj_version() == 336, "comparator admission requires MuJoCo 3.3.6");

    char error[1024] = {};
    ModelPtr nominal(mj_loadXML(argv[1], nullptr, error, sizeof(error)),
                     mj_deleteModel);
    Require(nominal != nullptr,
            std::string("could not load pinned task_flat.xml: ") + error);
    Require(nominal->nu == kActuatorCount && nominal->nq == 19 &&
                nominal->nv == 18 && nominal->nkey > 0,
            "pinned QuadrupedFlat model dimensions changed");
    Require(mj_name2id(nominal.get(), mjOBJ_KEY, "home") == 0,
            "pinned home keyframe identity changed");
    Require(std::abs(nominal->opt.timestep - kExpectedPlantStep) < 1.0e-12,
            "pinned task plant timestep changed");

    // Fail closed on source semantics before applying any compatibility edit.
    for (int actuator = 0; actuator < nominal->nu; ++actuator) {
      const double* gain = nominal->actuator_gainprm + actuator * mjNGAIN;
      const double* bias = nominal->actuator_biasprm + actuator * mjNBIAS;
      Require(nominal->actuator_gaintype[actuator] == mjGAIN_FIXED,
              "nominal actuator gain type drifted");
      Require(nominal->actuator_biastype[actuator] == mjBIAS_NONE,
              "nominal actuator bias type is no longer non-affine");
      Require(std::abs(gain[0] - 60.0) < 1.0e-12,
              "nominal actuator gainprm[0] drifted from 60");
      Require(std::abs(bias[0]) < 1.0e-12 &&
                  std::abs(bias[1] + 60.0) < 1.0e-12 &&
                  std::abs(bias[2] + 5.0) < 1.0e-12,
              "nominal actuator biasprm drifted from 0 -60 -5");
    }

    ModelPtr comparator_model(mj_copyModel(nullptr, nominal.get()),
                              mj_deleteModel);
    Require(comparator_model != nullptr,
            "could not create source-conditioned comparator model copy");
    for (int actuator = 0; actuator < comparator_model->nu; ++actuator) {
      comparator_model->actuator_biastype[actuator] = mjBIAS_AFFINE;
    }

    const HoldResult hold = RunHomeHold(nominal.get(), comparator_model.get());
    const ProbeResult probe = RunAgentProbe(comparator_model.get());
    const bool all_finite = hold.finite && probe.finite;

    std::cout << std::setprecision(17)
              << "{\"source_commit\":\"" << GO2_MJPC_SOURCE_COMMIT
              << "\",\"mujoco_version\":\"" << mj_versionString()
              << "\",\"compiler\":\"" << GO2_CXX_COMPILER_ID << " "
              << GO2_CXX_COMPILER_VERSION
              << "\",\"compiler_flags\":[\"-fno-strict-aliasing\"]"
              << ",\"task\":\"QuadrupedFlat\""
              << ",\"model\":{\"nq\":" << nominal->nq
              << ",\"nv\":" << nominal->nv << ",\"nu\":" << nominal->nu
              << ",\"plant_timestep_s\":" << nominal->opt.timestep << "}"
              << ",\"compatibility\":{\"source_validated\":true"
              << ",\"source_gainprm\":60"
              << ",\"source_biasprm\":[0,-60,-5]"
              << ",\"source_biastype\":\"mjBIAS_NONE\""
              << ",\"correction\":\"actuator biastype=mjBIAS_AFFINE\""
              << ",\"correction_scope\":\"ephemeral comparator model copy only\""
              << ",\"canonical_evaluation_plant_modified\":false}"
              << ",\"command\":{\"mode\":\"Walk\",\"gait_switch\":\"Manual\""
              << ",\"gait\":\"Trot\",\"walk_speed_mps\":1"
              << ",\"walk_turn_radps\":0}"
              << ",\"home_hold\":{\"steps\":" << kHomeHoldSteps
              << ",\"simulated_seconds\":" << hold.simulated_seconds
              << ",\"uncorrected_force_max\":" << hold.uncorrected_force_max
              << ",\"corrected_force_max\":" << hold.corrected_force_max
              << ",\"height_min_m\":" << hold.min_height
              << ",\"height_max_m\":" << hold.max_height
              << ",\"xy_displacement_m\":" << hold.xy_displacement
              << ",\"max_joint_error_rad\":" << hold.max_joint_error
              << ",\"finite\":" << (hold.finite ? "true" : "false")
              << ",\"passed\":" << (hold.passed ? "true" : "false") << "}"
              << ",\"agent_probe\":{\"planning_updates\":" << probe.planning_updates
              << ",\"plant_steps\":" << probe.plant_steps
              << ",\"simulated_seconds\":" << probe.simulated_seconds
              << ",\"wall_seconds\":" << probe.wall_seconds
              << ",\"planning_wall_seconds\":" << probe.planning_wall_seconds
              << ",\"height_initial_m\":" << probe.height_initial
              << ",\"height_min_m\":" << probe.height_min
              << ",\"height_max_m\":" << probe.height_max
              << ",\"height_final_m\":" << probe.height_final
              << ",\"displacement_x_m\":" << probe.displacement_x
              << ",\"displacement_y_m\":" << probe.displacement_y
              << ",\"displacement_xy_m\":" << probe.displacement_xy
              << ",\"plan_time_p50_ms\":" << probe.plan_time_p50_ms
              << ",\"plan_time_p95_ms\":" << probe.plan_time_p95_ms
              << ",\"plan_time_max_ms\":" << probe.plan_time_max_ms
              << ",\"mode_walk\":" << (probe.mode_walk ? "true" : "false")
              << ",\"finite\":" << (probe.finite ? "true" : "false") << "}"
              << ",\"timing\":{\"home_hold_simulated_seconds\":"
              << hold.simulated_seconds << ",\"agent_probe_simulated_seconds\":"
              << probe.simulated_seconds << ",\"agent_probe_wall_seconds\":"
              << probe.wall_seconds << ",\"planning_wall_seconds\":"
              << probe.planning_wall_seconds << "}"
              << ",\"nonfinite_status\":\""
              << (all_finite ? "all_checked_values_finite" : "nonfinite_detected")
              << "\"}\n";

    return hold.passed && probe.finite && probe.mode_walk ? 0 : 1;
  } catch (const std::exception& exc) {
    std::cerr << "comparator admission failed: " << exc.what() << "\n";
    return 2;
  }
}
