#define main replay_bridge_atomic_legacy_main
#include "replay_bridge_atomic.cpp"
#undef main

#include "go2_forward_kinematics.h"
#include "go2_leg_jacobian.h"

#include <Eigen/Dense>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace
{
constexpr double kMaxJoinGapMs = 10.0;
constexpr double kDqLimit = 10.0;
constexpr double kConditionLimit = 1.0e4;
constexpr double kRankTolerance = 1.0e-12;
constexpr double kSolveResidualLimit = 1.0e-6;
constexpr double kInvalidFractionLimit = 0.05;
constexpr int kStanceJointCount = 3;
constexpr char kLegLabels[] = "FR,FL,RR,RL";

struct ControllerRow
{
  double active_time_s = std::numeric_limits<double>::quiet_NaN();
  int controller_contact_mask = 0;
  int physical_contact_mask = 0;
  bool have_controller_contact_mask = false;
  bool have_physical_contact_mask = false;
};

struct Target
{
  const Snapshot *snapshot = nullptr;
  ControllerRow controller;
  std::int64_t controller_join_delta_ms = 0;
};

struct LegSolution
{
  bool controller_stance = false;
  bool solve_valid = false;
  int rank = 0;
  double singular0 = std::numeric_limits<double>::quiet_NaN();
  double singular1 = std::numeric_limits<double>::quiet_NaN();
  double singular2 = std::numeric_limits<double>::quiet_NaN();
  double condition = std::numeric_limits<double>::quiet_NaN();
  double pre_residual = std::numeric_limits<double>::quiet_NaN();
  double post_residual = std::numeric_limits<double>::quiet_NaN();
  int clamped_joint_count = 0;
  std::array<double, 3> foot_body{};
  std::array<double, 3> omega_body{};
  std::array<double, 3> base_velocity_body{};
  std::array<double, 3> required_velocity_body{};
  std::array<double, 3> dq_actual{};
  std::array<double, 3> dq_unclamped{};
  std::array<double, 3> dq_clamped{};
  std::array<double, 3> implied_actual{};
  std::array<double, 3> mismatch_actual{};
  std::array<double, 3> implied_candidate{};
  std::array<std::array<double, 3>, 3> jacobian{};
};

std::string CsvEscape(const std::string &value)
{
  if (value.find_first_of(",\"\n\r") == std::string::npos)
    return value;
  std::string escaped = "\"";
  for (const char character : value)
  {
    if (character == '\"')
      escaped += '\"';
    escaped += character;
  }
  escaped += '\"';
  return escaped;
}

std::map<std::int64_t, ControllerRow> ReadControllerRows(
    const std::string &path, std::set<std::int64_t> &duplicate_ticks)
{
  std::ifstream input(path);
  if (!input)
    throw std::runtime_error("cannot open controller closure CSV: " + path);

  std::string line;
  if (!std::getline(input, line))
    throw std::runtime_error("controller closure CSV is empty");
  if (!line.empty() && line.back() == '\r')
    line.pop_back();
  const std::vector<std::string> header = SplitCsv(line);
  std::unordered_map<std::string, std::size_t> columns;
  for (std::size_t i = 0; i < header.size(); ++i)
    columns.emplace(header[i], i);

  std::map<std::int64_t, ControllerRow> rows;
  while (std::getline(input, line))
  {
    if (!line.empty() && line.back() == '\r')
      line.pop_back();
    if (line.empty())
      continue;
    const std::vector<std::string> fields = SplitCsv(line);
    double active_time = 0.0;
    double tick_s = 0.0;
    if (!GetDouble(fields, columns, "active_relative_time_s", active_time) ||
        !GetDouble(fields, columns, "state_tick_s", tick_s))
      continue;
    ControllerRow row;
    row.active_time_s = active_time;
    row.have_controller_contact_mask = GetInt(
        fields, columns, "solver_contact_mask",
        row.controller_contact_mask);
    row.have_physical_contact_mask = GetInt(
        fields, columns, "physical_contact_mask",
        row.physical_contact_mask);
    const std::int64_t tick_ms = static_cast<std::int64_t>(
        std::llround(tick_s * 1000.0));
    if (rows.find(tick_ms) != rows.end())
      duplicate_ticks.insert(tick_ms);
    else
      rows.emplace(tick_ms, row);
  }
  return rows;
}

const std::pair<const std::int64_t, ControllerRow> *NearestControllerRow(
    const std::map<std::int64_t, ControllerRow> &rows,
    std::int64_t tick_ms, std::int64_t &delta_ms)
{
  if (rows.empty())
    return nullptr;
  auto upper = rows.lower_bound(tick_ms);
  auto best = rows.end();
  if (upper != rows.end())
    best = upper;
  if (upper != rows.begin())
  {
    auto previous = std::prev(upper);
    if (best == rows.end() ||
        std::llabs(previous->first - tick_ms) <=
            std::llabs(best->first - tick_ms))
      best = previous;
  }
  if (best == rows.end())
    return nullptr;
  delta_ms = best->first - tick_ms;
  return &*best;
}

std::array<double, 3> ToArray(const mjtNum *values)
{
  return {static_cast<double>(values[0]), static_cast<double>(values[1]),
          static_cast<double>(values[2])};
}

std::array<double, 3> Cross(
    const std::array<double, 3> &a, const std::array<double, 3> &b)
{
  return {a[1] * b[2] - a[2] * b[1],
          a[2] * b[0] - a[0] * b[2],
          a[0] * b[1] - a[1] * b[0]};
}

std::array<double, 3> Add(
    const std::array<double, 3> &a, const std::array<double, 3> &b)
{
  return {a[0] + b[0], a[1] + b[1], a[2] + b[2]};
}

std::array<double, 3> Subtract(
    const std::array<double, 3> &a, const std::array<double, 3> &b)
{
  return {a[0] - b[0], a[1] - b[1], a[2] - b[2]};
}

std::array<double, 3> Scale(
    const std::array<double, 3> &a, double scale)
{
  return {scale * a[0], scale * a[1], scale * a[2]};
}

double Norm(const std::array<double, 3> &value)
{
  return std::sqrt(value[0] * value[0] + value[1] * value[1] +
                   value[2] * value[2]);
}

std::array<double, 3> ClampDq(
    const std::array<double, 3> &value, int &clamped_count)
{
  std::array<double, 3> result{};
  for (int i = 0; i < 3; ++i)
  {
    result[i] = std::clamp(value[i], -kDqLimit, kDqLimit);
    if (result[i] != value[i])
      ++clamped_count;
  }
  return result;
}

Eigen::Matrix3d EigenJacobian(
    const go2_control::LegFootJacobian &jacobian)
{
  Eigen::Matrix3d result;
  for (int row = 0; row < 3; ++row)
    for (int col = 0; col < 3; ++col)
      result(row, col) = jacobian[row][col];
  return result;
}

std::array<double, 3> EigenArray(const Eigen::Vector3d &value)
{
  return {value(0), value(1), value(2)};
}

LegSolution SolveLeg(
    const mjModel *model, const mjData *data, int leg,
    int controller_contact_mask,
    const std::array<double, 3> &q_des,
    const std::array<double, 3> &dq_actual)
{
  LegSolution result;
  result.controller_stance = (controller_contact_mask & (1 << leg)) != 0;
  result.dq_actual = dq_actual;

  const go2::Leg typed_leg = static_cast<go2::Leg>(leg);
  const go2::Vec3 foot = go2::FootPosition(
      typed_leg, q_des[0], q_des[1], q_des[2]);
  result.foot_body = {foot.x, foot.y, foot.z};
  const go2_control::LegFootJacobian repository_jacobian =
      go2_control::FootJacobian(
          typed_leg, q_des[0], q_des[1], q_des[2]);
  result.jacobian = repository_jacobian;

  mjtNum spatial_velocity[6] = {};
  const int base_body = mj_name2id(model, mjOBJ_BODY, "base_link");
  if (base_body < 0)
    throw std::runtime_error("base_link body is missing");
  mj_objectVelocity(model, data, mjOBJ_BODY, base_body,
                    spatial_velocity, 1);
  result.omega_body = ToArray(spatial_velocity);
  result.base_velocity_body = ToArray(spatial_velocity + 3);
  result.required_velocity_body = Scale(
      Add(result.base_velocity_body, Cross(result.omega_body, result.foot_body)),
      -1.0);

  const Eigen::Matrix3d jacobian_matrix = EigenJacobian(repository_jacobian);
  const Eigen::Vector3d required(
      result.required_velocity_body[0], result.required_velocity_body[1],
      result.required_velocity_body[2]);
  const Eigen::JacobiSVD<Eigen::Matrix3d> svd(
      jacobian_matrix, Eigen::ComputeFullU | Eigen::ComputeFullV);
  const Eigen::Vector3d singular_values = svd.singularValues();
  result.singular0 = singular_values(0);
  result.singular1 = singular_values(1);
  result.singular2 = singular_values(2);
  const double singular_max = singular_values(0);
  const double singular_min = singular_values(2);
  result.condition = singular_min > 0.0
      ? singular_max / singular_min
      : std::numeric_limits<double>::infinity();
  for (int i = 0; i < 3; ++i)
    if (singular_values(i) > kRankTolerance)
      ++result.rank;

  const Eigen::Vector3d actual(
      result.dq_actual[0], result.dq_actual[1], result.dq_actual[2]);
  result.implied_actual = EigenArray(jacobian_matrix * actual);
  result.mismatch_actual = Subtract(
      result.implied_actual, result.required_velocity_body);

  if (!result.controller_stance)
    return result;

  if (result.rank != 3 || !std::isfinite(result.condition) ||
      result.condition > kConditionLimit)
    return result;

  const Eigen::Vector3d solved = svd.solve(required);
  result.dq_unclamped = EigenArray(solved);
  result.pre_residual = Norm(Subtract(
      EigenArray(jacobian_matrix * solved), result.required_velocity_body));
  if (!std::isfinite(result.pre_residual) ||
      result.pre_residual > kSolveResidualLimit)
    return result;

  result.solve_valid = true;
  result.dq_clamped = ClampDq(result.dq_unclamped,
                              result.clamped_joint_count);
  const Eigen::Vector3d clamped(
      result.dq_clamped[0], result.dq_clamped[1], result.dq_clamped[2]);
  result.implied_candidate = EigenArray(jacobian_matrix * clamped);
  result.post_residual = Norm(Subtract(
      result.implied_candidate, result.required_velocity_body));
  return result;
}

void WriteCounterfactualHeader(std::ofstream &output)
{
  output << "active_relative_time_s,state_tick_s,sim_time_s,record_index"
         << ",controller_join_delta_ms,controller_contact_mask"
         << ",closure_physical_contact_mask,snapshot_physical_contact_mask"
         << ",actual_physical_contact_mask,candidate_physical_contact_mask"
         << ",qacc_live0_mps2,qacc_actual0_mps2,qacc_candidate0_mps2"
         << ",delta_ax_mps2,actual_replay_residual_mps2"
         << ",snapshot_ctrl_residual_Nm,bridge_formula_residual_Nm"
         << ",candidate_formula_residual_Nm,max_q_des_delta"
         << ",max_kp_delta,max_kd_delta,max_tau_ff_delta"
         << ",max_swing_dq_delta,stance_leg_count,solved_leg_count"
         << ",invalid_leg_count,stance_clamped_joint_count"
         << ",stance_joint_count,max_post_clamp_residual_mps";
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",q_des_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",dq_actual_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",dq_candidate_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",dq_sensor_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",kp_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",kd_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",tau_ff_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",d_target_actual_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",d_target_candidate_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",delta_d_target_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",dq_actual_minus_sensor_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",dq_candidate_minus_sensor_" << motor;
  output << "\n";
}

void WriteLegHeader(std::ofstream &output)
{
  output << "active_relative_time_s,state_tick_s,sim_time_s,record_index"
         << ",leg,controller_stance,closure_physical_stance"
         << ",snapshot_physical_stance,actual_physical_stance"
         << ",candidate_physical_stance";
  for (const char *name : {"foot_x_body_m", "foot_y_body_m", "foot_z_body_m",
                           "omega_x_body_radps", "omega_y_body_radps",
                           "omega_z_body_radps", "base_vx_body_mps",
                           "base_vy_body_mps", "base_vz_body_mps",
                           "required_vx_body_mps", "required_vy_body_mps",
                           "required_vz_body_mps"})
    output << "," << name;
  for (int row = 0; row < 3; ++row)
    for (int col = 0; col < 3; ++col)
      output << ",J_" << row << col;
  output << ",singular0,singular1,singular2,rank,condition_number"
         << ",solve_valid,pre_clamp_residual_mps,post_clamp_residual_mps"
         << ",clamped_joint_count";
  for (const char *prefix : {"dq_actual", "dq_unclamped", "dq_clamped",
                             "implied_actual", "actual_mismatch",
                             "implied_candidate"})
    for (int i = 0; i < 3; ++i)
      output << "," << prefix << "_" << i;
  output << "\n";
}

}  // namespace

int main(int argc, char **argv)
{
  if (argc != 6)
  {
    std::cerr << "usage: replay_stance_jacobian_dq <scene.xml> "
              << "<snapshots.bin> <closure.csv> <counterfactual.csv> "
              << "<legs.csv>\n";
    return 2;
  }

  try
  {
    std::set<std::int64_t> duplicate_closure_ticks;
    const auto controller_rows = ReadControllerRows(
        argv[3], duplicate_closure_ticks);
    if (!duplicate_closure_ticks.empty())
      throw std::runtime_error("ambiguous controller closure ticks");
    if (controller_rows.empty())
      throw std::runtime_error("controller closure has no rows");

    char error[1024] = {};
    mjModel *model = mj_loadXML(argv[1], nullptr, error, sizeof(error));
    if (model == nullptr)
      throw std::runtime_error(std::string("cannot load scene: ") + error);

    std::ifstream snapshot_input(argv[2], std::ios::binary);
    if (!snapshot_input)
      throw std::runtime_error("cannot open atomic snapshot file");
    SnapshotHeader header;
    if (!ReadSnapshotHeader(snapshot_input, header))
      throw std::runtime_error("atomic snapshot file is empty");
    if (header.mujoco_version != static_cast<std::uint32_t>(mj_version()) ||
        header.mjt_num_bytes != sizeof(mjtNum) ||
        header.nq != static_cast<std::uint32_t>(model->nq) ||
        header.nv != static_cast<std::uint32_t>(model->nv) ||
        header.na != static_cast<std::uint32_t>(model->na) ||
        header.nu != static_cast<std::uint32_t>(model->nu) ||
        header.state_sig != mjSTATE_INTEGRATION ||
        header.nu != kMotorCount)
      throw std::runtime_error("atomic snapshot/model signature mismatch");

    std::vector<Snapshot> snapshots;
    Snapshot snapshot;
    while (ReadSnapshot(snapshot_input, header, snapshot))
      snapshots.push_back(std::move(snapshot));
    if (snapshots.empty())
      throw std::runtime_error("atomic snapshot file has no records");

    std::uint64_t previous_seq = 0;
    std::uint32_t previous_step_index = 0;
    bool have_previous = false;
    for (const Snapshot &current : snapshots)
    {
      const std::uint64_t sequence = current.bridge.bridge_ctrl_seq;
      if (sequence == 0 || current.bridge.motor_count != header.nu)
        throw std::runtime_error("invalid atomic bridge record");
      if (!have_previous)
      {
        if (current.bridge_seq_step_index != 1)
          throw std::runtime_error("first bridge sequence index is not one");
      }
      else if (sequence < previous_seq ||
               (sequence == previous_seq &&
                current.bridge_seq_step_index != previous_step_index + 1) ||
               (sequence != previous_seq &&
                current.bridge_seq_step_index != 1))
        throw std::runtime_error("non-monotonic atomic bridge sequence");
      previous_seq = sequence;
      previous_step_index = current.bridge_seq_step_index;
      have_previous = true;
    }

    std::vector<Target> targets;
    std::set<std::int64_t> target_ticks;
    for (const Snapshot &current : snapshots)
    {
      std::int64_t join_delta_ms = 0;
      const auto *nearest = NearestControllerRow(
          controller_rows, current.state_tick_ms, join_delta_ms);
      if (nearest == nullptr ||
          std::abs(static_cast<double>(join_delta_ms)) > kMaxJoinGapMs ||
          nearest->second.active_time_s < kTargetStart ||
          nearest->second.active_time_s >= kTargetEnd)
        continue;
      if (!nearest->second.have_controller_contact_mask ||
          !nearest->second.have_physical_contact_mask)
        throw std::runtime_error("target closure row lacks contact masks");
      if (!target_ticks.insert(current.state_tick_ms).second)
        throw std::runtime_error("duplicate target snapshot tick");
      targets.push_back(Target{&current, nearest->second, join_delta_ms});
    }
    if (targets.size() != 552)
      throw std::runtime_error("expected exactly 552 target snapshots");

    std::array<int, 4> foot_geom_ids = {-1, -1, -1, -1};
    const char *foot_names[] = {"FR", "FL", "RR", "RL"};
    for (int leg = 0; leg < 4; ++leg)
      foot_geom_ids[leg] = mj_name2id(model, mjOBJ_GEOM, foot_names[leg]);
    const int base_body = mj_name2id(model, mjOBJ_BODY, "base_link");
    if (base_body < 0)
      throw std::runtime_error("base_link body is missing");

    std::ofstream output(argv[4]);
    std::ofstream leg_output(argv[5]);
    if (!output || !leg_output)
      throw std::runtime_error("cannot open counterfactual output");
    output << std::setprecision(17);
    leg_output << std::setprecision(17);
    WriteCounterfactualHeader(output);
    WriteLegHeader(leg_output);

    mjData *actual = mj_makeData(model);
    mjData *candidate = mj_makeData(model);
    if (actual == nullptr || candidate == nullptr)
      throw std::runtime_error("cannot allocate replay data");

    double max_snapshot_ctrl_residual = 0.0;
    double max_formula_residual = 0.0;
    double max_actual_residual = 0.0;
    double max_candidate_formula_residual = 0.0;
    double max_q_des_delta = 0.0;
    double max_kp_delta = 0.0;
    double max_kd_delta = 0.0;
    double max_tau_ff_delta = 0.0;
    double max_swing_dq_delta = 0.0;
    int invalid_legs = 0;
    int stance_legs = 0;
    int solved_legs = 0;
    int stance_clamped_joints = 0;
    int stance_joints = 0;
    double max_post_clamp_residual = 0.0;

    for (const Target &target : targets)
    {
      const Snapshot &current = *target.snapshot;
      double snapshot_ctrl_residual = 0.0;
      double formula_residual = 0.0;
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
      {
        snapshot_ctrl_residual = std::max(
            snapshot_ctrl_residual,
            std::abs(current.snapshot_ctrl[motor] -
                     current.bridge.ctrl[motor]));
        const double formula = current.bridge.tau_ff[motor] +
            current.bridge.kp[motor] *
                (current.bridge.q[motor] - current.bridge.sensor_q[motor]) +
            current.bridge.kd[motor] *
                (current.bridge.dq[motor] - current.bridge.sensor_dq[motor]);
        formula_residual = std::max(
            formula_residual,
            std::abs(formula - current.bridge.ctrl[motor]));
      }
      max_snapshot_ctrl_residual = std::max(
          max_snapshot_ctrl_residual, snapshot_ctrl_residual);
      max_formula_residual = std::max(max_formula_residual, formula_residual);

      mj_setState(model, actual, current.state.data(), header.state_sig);
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        actual->ctrl[motor] = current.snapshot_ctrl[motor];
      mj_forward(model, actual);
      const double actual_qacc = static_cast<double>(actual->qacc[0]);
      const double actual_residual =
          std::abs(actual_qacc - current.live_qacc0);
      max_actual_residual = std::max(max_actual_residual, actual_residual);
      const ContactSummary actual_contact = Contacts(model, actual,
                                                       foot_geom_ids);

      std::array<double, kMotorCount> candidate_dq{};
      std::array<LegSolution, 4> legs{};
      int snapshot_stance_legs = 0;
      int snapshot_solved_legs = 0;
      int snapshot_invalid_legs = 0;
      int snapshot_clamped_joints = 0;
      int snapshot_stance_joints = 0;
      double snapshot_max_post_residual = 0.0;
      for (int leg = 0; leg < 4; ++leg)
      {
        const std::array<double, 3> q_des = {
            current.bridge.q[3 * leg + 0], current.bridge.q[3 * leg + 1],
            current.bridge.q[3 * leg + 2]};
        const std::array<double, 3> dq_actual = {
            current.bridge.dq[3 * leg + 0], current.bridge.dq[3 * leg + 1],
            current.bridge.dq[3 * leg + 2]};
        legs[leg] = SolveLeg(
            model, actual, leg, target.controller.controller_contact_mask,
            q_des, dq_actual);
        const LegSolution &solution = legs[leg];
        for (int joint = 0; joint < 3; ++joint)
          candidate_dq[3 * leg + joint] = solution.solve_valid
              ? solution.dq_clamped[joint]
              : dq_actual[joint];
        if (solution.controller_stance)
        {
          ++snapshot_stance_legs;
          snapshot_stance_joints += kStanceJointCount;
          if (solution.solve_valid)
          {
            ++snapshot_solved_legs;
            snapshot_clamped_joints += solution.clamped_joint_count;
            snapshot_max_post_residual = std::max(
                snapshot_max_post_residual, solution.post_residual);
          }
          else
            ++snapshot_invalid_legs;
        }

        const int physical_stance =
            (actual_contact.foot_mask & (1 << leg)) != 0 ? 1 : 0;
        leg_output << target.controller.active_time_s << ","
                   << current.state_tick_ms * 0.001 << "," << current.time_s
                   << "," << current.record_index << ","
                   << foot_names[leg] << ","
                   << (solution.controller_stance ? 1 : 0) << ","
                   << ((target.controller.physical_contact_mask & (1 << leg))
                           != 0 ? 1 : 0) << ","
                   << ((current.live_contact_mask & (1 << leg)) != 0 ? 1 : 0)
                   << "," << physical_stance << "," << physical_stance;
        for (double value : solution.foot_body)
          leg_output << "," << value;
        for (double value : solution.omega_body)
          leg_output << "," << value;
        for (double value : solution.base_velocity_body)
          leg_output << "," << value;
        for (double value : solution.required_velocity_body)
          leg_output << "," << value;
        for (int row = 0; row < 3; ++row)
          for (int col = 0; col < 3; ++col)
            leg_output << "," << solution.jacobian[row][col];
        leg_output << "," << solution.singular0
                   << "," << solution.singular1
                   << "," << solution.singular2
                   << "," << solution.rank
                   << "," << solution.condition
                   << "," << (solution.solve_valid ? 1 : 0)
                   << "," << solution.pre_residual
                   << "," << solution.post_residual
                   << "," << solution.clamped_joint_count;
        for (const auto &values : {solution.dq_actual,
                                   solution.dq_unclamped,
                                   solution.dq_clamped,
                                   solution.implied_actual,
                                   solution.mismatch_actual,
                                   solution.implied_candidate})
          for (double value : values)
            leg_output << "," << value;
        leg_output << "\n";
      }
      stance_legs += snapshot_stance_legs;
      solved_legs += snapshot_solved_legs;
      invalid_legs += snapshot_invalid_legs;
      stance_clamped_joints += snapshot_clamped_joints;
      stance_joints += snapshot_stance_joints;
      max_post_clamp_residual = std::max(
          max_post_clamp_residual, snapshot_max_post_residual);

      mj_setState(model, candidate, current.state.data(), header.state_sig);
      double candidate_formula_residual = 0.0;
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
      {
        const double candidate_ctrl = current.bridge.tau_ff[motor] +
            current.bridge.kp[motor] *
                (current.bridge.q[motor] - current.bridge.sensor_q[motor]) +
            current.bridge.kd[motor] *
                (candidate_dq[motor] - current.bridge.sensor_dq[motor]);
        candidate->ctrl[motor] = candidate_ctrl;
        const double reconstructed = current.bridge.tau_ff[motor] +
            current.bridge.kp[motor] *
                (current.bridge.q[motor] - current.bridge.sensor_q[motor]) +
            current.bridge.kd[motor] *
                (candidate_dq[motor] - current.bridge.sensor_dq[motor]);
        candidate_formula_residual = std::max(
            candidate_formula_residual,
            std::abs(reconstructed - candidate_ctrl));
      }
      max_candidate_formula_residual = std::max(
          max_candidate_formula_residual, candidate_formula_residual);
      mj_forward(model, candidate);
      const double candidate_qacc = static_cast<double>(candidate->qacc[0]);
      const double delta_ax = candidate_qacc - actual_qacc;
      const ContactSummary candidate_contact = Contacts(model, candidate,
                                                           foot_geom_ids);

      double max_q_des_delta = 0.0;
      double max_kp_delta_snapshot = 0.0;
      double max_kd_delta_snapshot = 0.0;
      double max_tau_ff_delta_snapshot = 0.0;
      double max_swing_dq_delta_snapshot = 0.0;
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
      {
        max_q_des_delta = std::max(max_q_des_delta, 0.0);
        max_kp_delta_snapshot = std::max(max_kp_delta_snapshot, 0.0);
        max_kd_delta_snapshot = std::max(max_kd_delta_snapshot, 0.0);
        max_tau_ff_delta_snapshot = std::max(max_tau_ff_delta_snapshot, 0.0);
        const int leg = motor / 3;
        if (!legs[leg].controller_stance)
          max_swing_dq_delta_snapshot = std::max(
              max_swing_dq_delta_snapshot,
              std::abs(candidate_dq[motor] - current.bridge.dq[motor]));
      }
      max_q_des_delta = std::max(max_q_des_delta, 0.0);
      max_kp_delta = std::max(max_kp_delta, max_kp_delta_snapshot);
      max_kd_delta = std::max(max_kd_delta, max_kd_delta_snapshot);
      max_tau_ff_delta = std::max(max_tau_ff_delta,
                                  max_tau_ff_delta_snapshot);
      max_swing_dq_delta = std::max(max_swing_dq_delta,
                                    max_swing_dq_delta_snapshot);

      output << target.controller.active_time_s << ","
             << current.state_tick_ms * 0.001 << "," << current.time_s
             << "," << current.record_index << ","
             << target.controller_join_delta_ms << ","
             << target.controller.controller_contact_mask << ","
             << target.controller.physical_contact_mask << ","
             << current.live_contact_mask << "," << actual_contact.foot_mask
             << "," << candidate_contact.foot_mask << ","
             << current.live_qacc0 << "," << actual_qacc << ","
             << candidate_qacc << "," << delta_ax << ","
             << actual_residual << "," << snapshot_ctrl_residual << ","
             << formula_residual << "," << candidate_formula_residual << ","
             << max_q_des_delta << "," << max_kp_delta_snapshot << ","
             << max_kd_delta_snapshot << "," << max_tau_ff_delta_snapshot
             << "," << max_swing_dq_delta_snapshot << ","
             << snapshot_stance_legs << "," << snapshot_solved_legs << ","
             << snapshot_invalid_legs << "," << snapshot_clamped_joints << ","
             << snapshot_stance_joints << "," << snapshot_max_post_residual;
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << current.bridge.q[motor];
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << current.bridge.dq[motor];
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << candidate_dq[motor];
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << current.bridge.sensor_dq[motor];
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << current.bridge.kp[motor];
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << current.bridge.kd[motor];
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << current.bridge.tau_ff[motor];
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << current.bridge.kd[motor] * current.bridge.dq[motor];
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << current.bridge.kd[motor] * candidate_dq[motor];
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << current.bridge.kd[motor] *
            (candidate_dq[motor] - current.bridge.dq[motor]);
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << current.bridge.dq[motor] -
            current.bridge.sensor_dq[motor];
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        output << "," << candidate_dq[motor] -
            current.bridge.sensor_dq[motor];
      output << "\n";
    }

    const double invalid_fraction = stance_legs > 0
        ? static_cast<double>(invalid_legs) / stance_legs : 0.0;
    const double clamp_fraction = stance_joints > 0
        ? static_cast<double>(stance_clamped_joints) / stance_joints : 0.0;
    std::cerr << "replay_stance_jacobian_dq targets=" << targets.size()
              << " stance_legs=" << stance_legs
              << " solved_legs=" << solved_legs
              << " invalid_legs=" << invalid_legs
              << " invalid_fraction=" << invalid_fraction
              << " clamp_fraction=" << clamp_fraction
              << " max_snapshot_ctrl_residual="
              << max_snapshot_ctrl_residual
              << " max_formula_residual=" << max_formula_residual
              << " max_actual_residual=" << max_actual_residual
              << " max_candidate_formula_residual="
              << max_candidate_formula_residual
              << " max_post_clamp_residual=" << max_post_clamp_residual
              << " validation="
              << (invalid_fraction <= kInvalidFractionLimit ? "PASS" : "FAIL")
              << "\n";

    mj_deleteData(actual);
    mj_deleteData(candidate);
    mj_deleteModel(model);
    return invalid_fraction <= kInvalidFractionLimit ? 0 : 1;
  }
  catch (const std::exception &error)
  {
    std::cerr << "replay_stance_jacobian_dq: " << error.what() << "\n";
    return 1;
  }
}
