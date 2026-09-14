#define main replay_bridge_atomic_legacy_main
#include "replay_bridge_atomic.cpp"
#undef main

#include <algorithm>
#include <array>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <string>
#include <vector>

namespace
{
struct Branch
{
  const char *name;
  bool remove_target;
  bool remove_sensor;
  bool thighs_only;
};

constexpr Branch kBranches[] = {
    {"ACTUAL", false, false, false},
    {"NO_D_ALL", true, true, false},
    {"NO_D_TARGET_ALL", true, false, false},
    {"NO_D_SENSOR_ALL", false, true, false},
    {"NO_D_TARGET_THIGHS", true, false, true},
    {"NO_D_SENSOR_THIGHS", false, true, true},
};

bool IsThigh(int motor)
{
  return motor == 1 || motor == 4 || motor == 7 || motor == 10;
}

double Quantile(std::vector<double> values, double probability)
{
  if (values.empty())
    return std::numeric_limits<double>::quiet_NaN();
  std::sort(values.begin(), values.end());
  const double index = probability * static_cast<double>(values.size() - 1);
  const std::size_t lower = static_cast<std::size_t>(std::floor(index));
  const std::size_t upper = std::min(lower + 1, values.size() - 1);
  return values[lower] + (values[upper] - values[lower]) *
      (index - static_cast<double>(lower));
}

double RestoreAndForward(
    const mjModel *model, mjData *data, const Snapshot &snapshot,
    const SnapshotHeader &header,
    const std::array<double, kMotorCount> &control)
{
  mj_setState(model, data, snapshot.state.data(), header.state_sig);
  for (std::size_t motor = 0; motor < kMotorCount; ++motor)
    data->ctrl[motor] = control[motor];
  mj_forward(model, data);
  return static_cast<double>(data->qacc[0]);
}

std::array<double, kMotorCount> BranchControl(
    const Snapshot &snapshot,
    const std::array<double, kMotorCount> &d_target,
    const std::array<double, kMotorCount> &d_sensor,
    const Branch &branch)
{
  std::array<double, kMotorCount> control = snapshot.snapshot_ctrl;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
  {
    if (branch.thighs_only && !IsThigh(motor))
      continue;
    if (branch.remove_target)
      control[motor] -= d_target[motor];
    if (branch.remove_sensor)
      control[motor] -= d_sensor[motor];
  }
  return control;
}

std::string PhaseBin(double phase)
{
  if (phase < 0.25)
    return "[0,0.25)";
  if (phase < 0.50)
    return "[0.25,0.5)";
  if (phase < 0.75)
    return "[0.5,0.75)";
  return "[0.75,1)";
}
}  // namespace

int main(int argc, char **argv)
{
  if (argc != 5)
  {
    std::cerr << "usage: replay_pd_d_decomposition <scene.xml> "
              << "<snapshots.bin> <diagnostic.csv> <output.csv>\n";
    return 2;
  }

  try
  {
    const auto diagnostics = ReadDiagnostics(argv[3]);
    char error[1024] = {};
    mjModel *model = mj_loadXML(argv[1], nullptr, error, sizeof(error));
    if (model == nullptr)
      throw std::runtime_error(std::string("cannot load scene: ") + error);

    std::ifstream snapshot_input(argv[2], std::ios::binary);
    if (!snapshot_input)
      throw std::runtime_error("cannot open snapshot file");
    SnapshotHeader header;
    if (!ReadSnapshotHeader(snapshot_input, header))
      throw std::runtime_error("snapshot file is empty");
    if (header.mujoco_version != static_cast<std::uint32_t>(mj_version()) ||
        header.mjt_num_bytes != sizeof(mjtNum) ||
        header.nq != static_cast<std::uint32_t>(model->nq) ||
        header.nv != static_cast<std::uint32_t>(model->nv) ||
        header.na != static_cast<std::uint32_t>(model->na) ||
        header.nu != static_cast<std::uint32_t>(model->nu) ||
        header.state_sig != mjSTATE_INTEGRATION ||
        header.nu != kMotorCount)
      throw std::runtime_error("snapshot/model signature mismatch");

    std::vector<Snapshot> snapshots;
    Snapshot snapshot;
    while (ReadSnapshot(snapshot_input, header, snapshot))
      snapshots.push_back(std::move(snapshot));
    if (snapshots.empty())
      throw std::runtime_error("snapshot file contains no records");

    std::uint64_t previous_seq = 0;
    std::uint32_t previous_step = 0;
    bool have_previous = false;
    for (const Snapshot &current : snapshots)
    {
      if (current.bridge.bridge_ctrl_seq == 0 ||
          current.bridge.motor_count != header.nu)
        throw std::runtime_error("invalid atomic bridge record");
      if (!have_previous)
      {
        if (current.bridge_seq_step_index != 1)
          throw std::runtime_error("first bridge sequence index is not one");
      }
      else if (current.bridge.bridge_ctrl_seq < previous_seq)
        throw std::runtime_error("bridge sequence is not monotonic");
      else if (current.bridge.bridge_ctrl_seq == previous_seq &&
               current.bridge_seq_step_index != previous_step + 1)
        throw std::runtime_error("bridge sequence reuse index is not consecutive");
      else if (current.bridge.bridge_ctrl_seq != previous_seq &&
               current.bridge_seq_step_index != 1)
        throw std::runtime_error("new bridge sequence does not start at one");
      previous_seq = current.bridge.bridge_ctrl_seq;
      previous_step = current.bridge_seq_step_index;
      have_previous = true;
    }

    std::vector<const Snapshot *> targets;
    std::map<std::int64_t, const DiagnosticRow *> target_diagnostics;
    std::map<std::int64_t, std::int64_t> target_deltas;
    for (const Snapshot &current : snapshots)
    {
      std::int64_t delta_ms = 0;
      const DiagnosticRow *diagnostic = NearestDiagnostic(
          diagnostics, current.state_tick_ms, delta_ms);
      if (diagnostic == nullptr ||
          std::llabs(delta_ms) > kMaxContextGapMs ||
          diagnostic->active_time_s < kTargetStart ||
          diagnostic->active_time_s >= kTargetEnd)
        continue;
      if (target_diagnostics.find(current.state_tick_ms) !=
          target_diagnostics.end())
        throw std::runtime_error("ambiguous target snapshot");
      targets.push_back(&current);
      target_diagnostics.emplace(current.state_tick_ms, diagnostic);
      target_deltas.emplace(current.state_tick_ms, delta_ms);
    }
    if (targets.size() != 552)
      throw std::runtime_error("expected exactly 552 validated target snapshots");

    mjData *actual = mj_makeData(model);
    mjData *branch = mj_makeData(model);
    if (actual == nullptr || branch == nullptr)
      throw std::runtime_error("cannot allocate replay data");

    std::ofstream output(argv[4]);
    if (!output)
      throw std::runtime_error("cannot open decomposition output");
    output << std::setprecision(17);
    output << "active_relative_time_s,state_tick_s,sim_time_s,gait_phase,phase_bin"
           << ",diagnostic_tick_delta_ms,replay_contact_mask,live_contact_mask"
           << ",qacc_live0_mps2,qacc_actual0_mps2,actual_replay_residual_mps2"
           << ",bridge_formula_residual_Nm,snapshot_ctrl_residual_Nm";
    for (const Branch &definition : kBranches)
      if (std::string(definition.name) != "ACTUAL")
        output << ",qacc_" << definition.name << "_mps2,delta_"
               << definition.name << "_mps2";
    for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
      output << ",kd_" << motor << ",dq_des_" << motor
             << ",dq_sensor_" << motor << ",d_target_" << motor
             << ",d_sensor_" << motor << ",d_total_" << motor;
    output << "\n";

    double max_ctrl_residual = 0.0;
    double max_formula_residual = 0.0;
    double max_actual_residual = 0.0;
    std::vector<double> no_d_all_deltas;
    no_d_all_deltas.reserve(targets.size());

    for (const Snapshot *current : targets)
    {
      const DiagnosticRow &diagnostic =
          *target_diagnostics.at(current->state_tick_ms);
      double snapshot_ctrl_residual = 0.0;
      double formula_residual = 0.0;
      std::array<double, kMotorCount> d_target{};
      std::array<double, kMotorCount> d_sensor{};
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
      {
        snapshot_ctrl_residual = std::max(
            snapshot_ctrl_residual,
            std::abs(current->snapshot_ctrl[motor] -
                     current->bridge.ctrl[motor]));
        const double p = current->bridge.kp[motor] *
            (current->bridge.q[motor] - current->bridge.sensor_q[motor]);
        d_target[motor] = current->bridge.kd[motor] *
            current->bridge.dq[motor];
        d_sensor[motor] = -current->bridge.kd[motor] *
            current->bridge.sensor_dq[motor];
        formula_residual = std::max(
            formula_residual,
            std::abs(current->bridge.tau_ff[motor] + p +
                     d_target[motor] + d_sensor[motor] -
                     current->bridge.ctrl[motor]));
      }
      max_ctrl_residual = std::max(max_ctrl_residual, snapshot_ctrl_residual);
      max_formula_residual = std::max(max_formula_residual, formula_residual);

      const double actual_qacc = RestoreAndForward(
          model, actual, *current, header, current->snapshot_ctrl);
      const double actual_residual =
          std::abs(actual_qacc - current->live_qacc0);
      max_actual_residual = std::max(max_actual_residual, actual_residual);
      const ContactSummary replay_contact = Contacts(
          model, actual, std::array<int, 4>{
              mj_name2id(model, mjOBJ_GEOM, "FR"),
              mj_name2id(model, mjOBJ_GEOM, "FL"),
              mj_name2id(model, mjOBJ_GEOM, "RR"),
              mj_name2id(model, mjOBJ_GEOM, "RL")});

      const double phase = std::fmod(diagnostic.active_time_s / 0.14, 1.0) < 0.0
          ? std::fmod(diagnostic.active_time_s / 0.14, 1.0) + 1.0
          : std::fmod(diagnostic.active_time_s / 0.14, 1.0);
      output << diagnostic.active_time_s << ","
             << current->state_tick_ms * 0.001 << "," << current->time_s
             << "," << phase << ",\"" << PhaseBin(phase) << "\","
             << target_deltas.at(current->state_tick_ms) << ","
             << replay_contact.foot_mask << "," << current->live_contact_mask
             << "," << current->live_qacc0 << "," << actual_qacc << ","
             << actual_residual << "," << formula_residual << ","
             << snapshot_ctrl_residual;

      for (const Branch &definition : kBranches)
      {
        if (std::string(definition.name) == "ACTUAL")
          continue;
        const auto control = BranchControl(
            *current, d_target, d_sensor, definition);
        const double qacc = RestoreAndForward(
            model, branch, *current, header, control);
        const double delta_ax = qacc - actual_qacc;
        output << "," << qacc << "," << delta_ax;
        if (std::string(definition.name) == "NO_D_ALL")
          no_d_all_deltas.push_back(delta_ax);
      }
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << current->bridge.kd[motor]
               << "," << current->bridge.dq[motor]
               << "," << current->bridge.sensor_dq[motor]
               << "," << d_target[motor]
               << "," << d_sensor[motor]
               << "," << (d_target[motor] + d_sensor[motor]);
      output << "\n";
    }

    constexpr double kPriorNoDMedian = -7.0863729950363012;
    const double no_d_all_median = Quantile(no_d_all_deltas, 0.50);
    constexpr double kCtrlGate = 1.0e-12;
    constexpr double kFormulaGate = 1.0e-10;
    constexpr double kQaccGate = 1.0e-5;
    if (max_ctrl_residual > kCtrlGate ||
        max_formula_residual > kFormulaGate ||
        max_actual_residual > kQaccGate ||
        std::abs(no_d_all_median - kPriorNoDMedian) > 1.0e-12)
      throw std::runtime_error(
          "decomposition validation gate failed: ctrl=" +
          std::to_string(max_ctrl_residual) + " formula=" +
          std::to_string(max_formula_residual) + " qacc=" +
          std::to_string(max_actual_residual) + " no_d_all=" +
          std::to_string(no_d_all_median));

    std::cerr << "replay_pd_d_decomposition targets=" << targets.size()
              << " max_ctrl_residual=" << max_ctrl_residual
              << " max_formula_residual=" << max_formula_residual
              << " max_actual_residual=" << max_actual_residual
              << " no_d_all_median=" << no_d_all_median
              << " prior_delta=" << (no_d_all_median - kPriorNoDMedian)
              << " validation=PASS\n";
    mj_deleteData(actual);
    mj_deleteData(branch);
    mj_deleteModel(model);
    return 0;
  }
  catch (const std::exception &error)
  {
    std::cerr << "replay_pd_d_decomposition: " << error.what() << "\n";
    return 1;
  }
}
