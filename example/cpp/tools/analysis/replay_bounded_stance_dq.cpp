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
        fields, columns, "solver_contact_mask", row.controller_contact_mask);
    row.have_physical_contact_mask = GetInt(
        fields, columns, "physical_contact_mask", row.physical_contact_mask);
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

std::array<double, 3> Cross(const std::array<double, 3> &a,
                            const std::array<double, 3> &b)
{
  return {a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
          a[0] * b[1] - a[1] * b[0]};
}

std::array<double, 3> Add(const std::array<double, 3> &a,
                          const std::array<double, 3> &b)
{
  return {a[0] + b[0], a[1] + b[1], a[2] + b[2]};
}

std::array<double, 3> Subtract(const std::array<double, 3> &a,
                               const std::array<double, 3> &b)
{
  return {a[0] - b[0], a[1] - b[1], a[2] - b[2]};
}

std::array<double, 3> Scale(const std::array<double, 3> &a, double scale)
{
  return {scale * a[0], scale * a[1], scale * a[2]};
}

double Norm(const std::array<double, 3> &value)
{
  return std::sqrt(value[0] * value[0] + value[1] * value[1] +
                   value[2] * value[2]);
}

std::array<double, 3> ClampDq(const std::array<double, 3> &value,
                              int &clamped_count)
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

Eigen::Matrix3d EigenJacobian(const go2_control::LegFootJacobian &jacobian)
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

LegSolution SolveLeg(const mjModel *model, const mjData *data, int leg,
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
      go2_control::FootJacobian(typed_leg, q_des[0], q_des[1], q_des[2]);
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
  const Eigen::Vector3d required(result.required_velocity_body[0],
                                 result.required_velocity_body[1],
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
  const Eigen::Vector3d actual(result.dq_actual[0], result.dq_actual[1],
                               result.dq_actual[2]);
  result.implied_actual = EigenArray(jacobian_matrix * actual);
  result.mismatch_actual = Subtract(result.implied_actual,
                                    result.required_velocity_body);
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
  const Eigen::Vector3d clamped(result.dq_clamped[0], result.dq_clamped[1],
                                result.dq_clamped[2]);
  result.implied_candidate = EigenArray(jacobian_matrix * clamped);
  result.post_residual = Norm(Subtract(
      result.implied_candidate, result.required_velocity_body));
  return result;
}

constexpr double kBoundedDqLimit = 2.0;
constexpr double kLimiterEpsilon = 1.0e-12;

struct CandidateSpec
{
  const char *name;
  double d_target_cap;
};

constexpr CandidateSpec kCandidates[] = {
    {"BOUND_D2", 2.0}, {"BOUND_D4", 4.0}, {"BOUND_D6", 6.0}};

struct BoundedLeg
{
  bool controller_stance = false;
  bool solve_valid = false;
  int rank = 0;
  double singular0 = std::numeric_limits<double>::quiet_NaN();
  double singular1 = std::numeric_limits<double>::quiet_NaN();
  double singular2 = std::numeric_limits<double>::quiet_NaN();
  double condition = std::numeric_limits<double>::quiet_NaN();
  double pre_residual = std::numeric_limits<double>::quiet_NaN();
  double full_post_residual = std::numeric_limits<double>::quiet_NaN();
  double s_leg = std::numeric_limits<double>::quiet_NaN();
  double dq_scalar_limit = std::numeric_limits<double>::infinity();
  double d_scalar_limit = std::numeric_limits<double>::infinity();
  std::string limiter = "SWING_UNCHANGED";
  bool correction_zero = true;
  std::array<double, 3> dq_base{};
  std::array<double, 3> dq_ss_unclamped{};
  std::array<double, 3> dq_ss{};
  std::array<double, 3> delta_dq_raw{};
  std::array<double, 3> delta_dq{};
  std::array<double, 3> dq_candidate{};
  std::array<double, 3> kd{};
  std::array<double, 3> delta_d_target{};
  std::array<double, 3> required_velocity{};
  std::array<double, 3> implied_actual{};
  std::array<double, 3> mismatch_actual{};
  std::array<double, 3> implied_candidate{};
  std::array<double, 3> mismatch_candidate{};
};

double ArrayNorm(const std::array<double, 3> &value)
{
  return std::sqrt(value[0] * value[0] + value[1] * value[1] +
                   value[2] * value[2]);
}

double MaxAbs(const std::array<double, 3> &value)
{
  return std::max({std::abs(value[0]), std::abs(value[1]),
                   std::abs(value[2])});
}

BoundedLeg MakeBoundedLeg(const LegSolution &solution,
                          const std::array<double, 3> &dq_base,
                          const std::array<double, 3> &kd,
                          const CandidateSpec &candidate)
{
  BoundedLeg result;
  result.controller_stance = solution.controller_stance;
  result.solve_valid = solution.solve_valid;
  result.rank = solution.rank;
  result.singular0 = solution.singular0;
  result.singular1 = solution.singular1;
  result.singular2 = solution.singular2;
  result.condition = solution.condition;
  result.pre_residual = solution.pre_residual;
  result.full_post_residual = solution.post_residual;
  result.dq_base = dq_base;
  result.kd = kd;
  result.required_velocity = solution.required_velocity_body;
  result.implied_actual = solution.implied_actual;
  result.mismatch_actual = solution.mismatch_actual;
  if (!solution.controller_stance)
  {
    result.dq_candidate = dq_base;
    result.delta_dq_raw = {0.0, 0.0, 0.0};
    result.delta_dq = {0.0, 0.0, 0.0};
    result.implied_candidate = solution.implied_actual;
    result.mismatch_candidate = solution.mismatch_actual;
    return result;
  }
  result.dq_ss_unclamped = solution.dq_unclamped;
  // The bounded screen applies one scalar to the complete full-rank SVD
  // solution.  Do not inherit the prior checkpoint's per-joint +/-10 clamp,
  // because that would change the three-joint correction direction first.
  result.dq_ss = solution.dq_unclamped;
  result.delta_dq_raw = Subtract(result.dq_ss, result.dq_base);
  const double max_delta_dq = MaxAbs(result.delta_dq_raw);
  const std::array<double, 3> raw_d_target = {
      kd[0] * result.delta_dq_raw[0], kd[1] * result.delta_dq_raw[1],
      kd[2] * result.delta_dq_raw[2]};
  const double max_delta_d_target = MaxAbs(raw_d_target);
  if (max_delta_dq > kLimiterEpsilon)
    result.dq_scalar_limit = kBoundedDqLimit / max_delta_dq;
  if (max_delta_d_target > kLimiterEpsilon)
    result.d_scalar_limit = candidate.d_target_cap / max_delta_d_target;
  result.s_leg = std::min({1.0, result.dq_scalar_limit,
                            result.d_scalar_limit});
  if (!std::isfinite(result.s_leg) || result.s_leg < 0.0)
    throw std::runtime_error("invalid bounded correction scalar");
  if (max_delta_dq <= kLimiterEpsilon)
  {
    result.limiter = "ZERO";
  }
  else if (result.s_leg >= 1.0 - kLimiterEpsilon)
  {
    result.limiter = "NONE";
  }
  else if (std::abs(result.dq_scalar_limit - result.d_scalar_limit) <=
           kLimiterEpsilon * std::max(1.0, std::min(result.dq_scalar_limit,
                                                     result.d_scalar_limit)))
  {
    result.limiter = "BOTH";
  }
  else if (result.dq_scalar_limit < result.d_scalar_limit)
  {
    result.limiter = "DQ_CAP";
  }
  else
  {
    result.limiter = "D_CAP";
  }
  for (int joint = 0; joint < 3; ++joint)
  {
    result.delta_dq[joint] = result.s_leg * result.delta_dq_raw[joint];
    result.dq_candidate[joint] = result.dq_base[joint] +
                                 result.delta_dq[joint];
    result.delta_d_target[joint] = kd[joint] * result.delta_dq[joint];
  }
  result.correction_zero = MaxAbs(result.delta_dq) <= kLimiterEpsilon;
  return result;
}

void WriteScreenHeader(std::ofstream &output)
{
  output << "candidate,active_relative_time_s,state_tick_s,sim_time_s,record_index"
         << ",controller_join_delta_ms,controller_contact_mask"
         << ",closure_physical_contact_mask,snapshot_physical_contact_mask"
         << ",actual_physical_contact_mask,candidate_physical_contact_mask"
         << ",qacc_actual0_mps2,qacc_candidate0_mps2,delta_ax_mps2"
         << ",actual_replay_residual_mps2,snapshot_ctrl_residual_Nm"
         << ",bridge_formula_residual_Nm,candidate_formula_residual_Nm"
         << ",max_q_des_delta,max_kp_delta,max_kd_delta,max_tau_ff_delta"
         << ",max_swing_dq_delta,max_dq_change_radps,max_d_target_change_Nm"
         << ",stance_leg_count,solved_leg_count,invalid_leg_count"
         << ",dq_cap_limited_legs,d_cap_limited_legs,both_limited_legs"
         << ",unlimited_legs,zero_correction_legs"
         << ",max_baseline_mismatch_norm_mps,max_candidate_mismatch_norm_mps"
         << "\n";
}

void WriteLegHeader(std::ofstream &output)
{
  output << "candidate,active_relative_time_s,state_tick_s,sim_time_s,record_index"
         << ",leg,controller_stance,solve_valid,controller_contact_mask"
         << ",closure_physical_stance,snapshot_physical_stance"
         << ",actual_physical_stance,candidate_physical_stance"
         << ",candidate_d_target_cap_Nm,s_leg,dq_scalar_limit,d_scalar_limit"
         << ",limiter,correction_zero,rank,singular0,singular1,singular2"
         << ",condition_number,pre_residual_mps,full_post_residual_mps";
  for (const char *prefix : {"dq_base", "dq_ss_unclamped", "dq_ss",
                             "delta_dq_raw", "delta_dq", "dq_candidate",
                             "kd", "delta_d_target", "required_velocity",
                             "implied_actual", "mismatch_actual",
                             "implied_candidate", "mismatch_candidate"})
    for (int i = 0; i < 3; ++i)
      output << "," << prefix << "_" << i;
  output << ",mismatch_actual_norm_mps,mismatch_candidate_norm_mps"
         << ",mismatch_actual_x_mps,mismatch_candidate_x_mps\n";
}

void WriteArray(std::ofstream &output, const std::array<double, 3> &value)
{
  for (double item : value)
    output << "," << item;
}

}  // namespace

int main(int argc, char **argv)
{
  if (argc != 7)
  {
    std::cerr << "usage: replay_bounded_stance_dq <scene.xml> "
              << "<snapshots.bin> <closure.csv> <screen.csv> <legs.csv> "
              << "<candidate-summary.txt>\n";
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
        header.state_sig != mjSTATE_INTEGRATION || header.nu != kMotorCount)
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
    std::ofstream summary_output(argv[6]);
    if (!output || !leg_output || !summary_output)
      throw std::runtime_error("cannot open bounded screen outputs");
    output << std::setprecision(17);
    leg_output << std::setprecision(17);
    summary_output << std::setprecision(17);
    WriteScreenHeader(output);
    WriteLegHeader(leg_output);

    mjData *actual = mj_makeData(model);
    mjData *candidate = mj_makeData(model);
    if (actual == nullptr || candidate == nullptr)
      throw std::runtime_error("cannot allocate replay data");

    double max_snapshot_ctrl_residual = 0.0;
    double max_formula_residual = 0.0;
    double max_actual_residual = 0.0;
    double max_candidate_formula_residual = 0.0;
    double max_dq_change = 0.0;
    double max_d_target_change = 0.0;
    double max_swing_dq_change = 0.0;
    int invalid_legs = 0;
    int stance_legs = 0;
    int solved_legs = 0;
    int target_join_failures = 0;
    int contact_mismatches = 0;
    int candidate_formula_rows = 0;

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

      std::array<LegSolution, 4> solutions{};
      std::array<std::array<double, 3>, 4> base_dq{};
      std::array<std::array<double, 3>, 4> kd{};
      for (int leg = 0; leg < 4; ++leg)
      {
        base_dq[leg] = {current.bridge.dq[3 * leg + 0],
                        current.bridge.dq[3 * leg + 1],
                        current.bridge.dq[3 * leg + 2]};
        kd[leg] = {current.bridge.kd[3 * leg + 0],
                   current.bridge.kd[3 * leg + 1],
                   current.bridge.kd[3 * leg + 2]};
        const std::array<double, 3> q_des = {
            current.bridge.q[3 * leg + 0], current.bridge.q[3 * leg + 1],
            current.bridge.q[3 * leg + 2]};
        solutions[leg] = SolveLeg(
            model, actual, leg, target.controller.controller_contact_mask,
            q_des, base_dq[leg]);
        if (solutions[leg].controller_stance)
        {
          ++stance_legs;
          if (solutions[leg].solve_valid)
            ++solved_legs;
          else
            ++invalid_legs;
        }
      }

      for (const CandidateSpec &candidate_spec : kCandidates)
      {
        std::array<BoundedLeg, 4> legs{};
        std::array<double, kMotorCount> candidate_dq{};
        int snapshot_stance_legs = 0;
        int snapshot_solved_legs = 0;
        int snapshot_invalid_legs = 0;
        int dq_cap_limited_legs = 0;
        int d_cap_limited_legs = 0;
        int both_limited_legs = 0;
        int unlimited_legs = 0;
        int zero_correction_legs = 0;
        double max_snapshot_dq_change = 0.0;
        double max_snapshot_d_target_change = 0.0;
        double max_baseline_mismatch_norm = 0.0;
        double max_candidate_mismatch_norm = 0.0;

        for (int leg = 0; leg < 4; ++leg)
        {
          legs[leg] = MakeBoundedLeg(
              solutions[leg], base_dq[leg], kd[leg], candidate_spec);
          for (int joint = 0; joint < 3; ++joint)
            candidate_dq[3 * leg + joint] = legs[leg].dq_candidate[joint];
          if (legs[leg].controller_stance)
          {
            ++snapshot_stance_legs;
            if (legs[leg].solve_valid)
              ++snapshot_solved_legs;
            else
              ++snapshot_invalid_legs;
            if (legs[leg].limiter == "DQ_CAP")
              ++dq_cap_limited_legs;
            else if (legs[leg].limiter == "D_CAP")
              ++d_cap_limited_legs;
            else if (legs[leg].limiter == "BOTH")
              ++both_limited_legs;
            else if (legs[leg].limiter == "NONE")
              ++unlimited_legs;
            if (legs[leg].correction_zero)
              ++zero_correction_legs;
            max_baseline_mismatch_norm = std::max(
                max_baseline_mismatch_norm,
                ArrayNorm(legs[leg].mismatch_actual));
            const Eigen::Matrix3d jacobian = EigenJacobian(
                solutions[leg].jacobian);
            const Eigen::Vector3d bounded(
                legs[leg].dq_candidate[0], legs[leg].dq_candidate[1],
                legs[leg].dq_candidate[2]);
            legs[leg].implied_candidate = EigenArray(jacobian * bounded);
            legs[leg].mismatch_candidate = Subtract(
                legs[leg].implied_candidate, legs[leg].required_velocity);
            max_candidate_mismatch_norm = std::max(
                max_candidate_mismatch_norm,
                ArrayNorm(legs[leg].mismatch_candidate));
          }
          max_snapshot_dq_change = std::max(
              max_snapshot_dq_change, MaxAbs(legs[leg].delta_dq));
          max_snapshot_d_target_change = std::max(
              max_snapshot_d_target_change,
              MaxAbs(legs[leg].delta_d_target));

          const int actual_physical_stance =
              (actual_contact.foot_mask & (1 << leg)) != 0 ? 1 : 0;
          leg_output << candidate_spec.name << ","
                     << target.controller.active_time_s << ","
                     << current.state_tick_ms * 0.001 << "," << current.time_s
                     << "," << current.record_index << "," << foot_names[leg]
                     << "," << (legs[leg].controller_stance ? 1 : 0) << ","
                     << (legs[leg].solve_valid ? 1 : 0) << ","
                     << target.controller.controller_contact_mask << ","
                     << ((target.controller.physical_contact_mask & (1 << leg))
                             != 0 ? 1 : 0)
                     << "," << ((current.live_contact_mask & (1 << leg)) != 0
                                      ? 1
                                      : 0)
                     << "," << actual_physical_stance << ",";
          leg_output << actual_physical_stance << ","
                     << candidate_spec.d_target_cap << "," << legs[leg].s_leg
                     << "," << legs[leg].dq_scalar_limit << ","
                     << legs[leg].d_scalar_limit << "," << legs[leg].limiter
                     << "," << (legs[leg].correction_zero ? 1 : 0) << ","
                     << legs[leg].rank << "," << legs[leg].singular0 << ","
                     << legs[leg].singular1 << "," << legs[leg].singular2
                     << "," << legs[leg].condition << ","
                     << legs[leg].pre_residual << ","
                     << legs[leg].full_post_residual;
          for (const auto &values : {
                   legs[leg].dq_base, legs[leg].dq_ss_unclamped,
                   legs[leg].dq_ss, legs[leg].delta_dq_raw,
                   legs[leg].delta_dq, legs[leg].dq_candidate, legs[leg].kd,
                   legs[leg].delta_d_target, legs[leg].required_velocity,
                   legs[leg].implied_actual, legs[leg].mismatch_actual,
                   legs[leg].implied_candidate, legs[leg].mismatch_candidate})
            WriteArray(leg_output, values);
          leg_output << "," << ArrayNorm(legs[leg].mismatch_actual) << ","
                     << ArrayNorm(legs[leg].mismatch_candidate) << ","
                     << legs[leg].mismatch_actual[0] << ","
                     << legs[leg].mismatch_candidate[0] << "\n";
        }

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
        ++candidate_formula_rows;
        max_candidate_formula_residual = std::max(
            max_candidate_formula_residual, candidate_formula_residual);
        mj_forward(model, candidate);
        const double candidate_qacc = static_cast<double>(candidate->qacc[0]);
        const double delta_ax = candidate_qacc - actual_qacc;
        const ContactSummary candidate_contact = Contacts(model, candidate,
                                                           foot_geom_ids);
        if (candidate_contact.foot_mask != actual_contact.foot_mask)
          ++contact_mismatches;
        max_dq_change = std::max(max_dq_change, max_snapshot_dq_change);
        max_d_target_change = std::max(max_d_target_change,
                                       max_snapshot_d_target_change);
        output << candidate_spec.name << "," << target.controller.active_time_s
               << "," << current.state_tick_ms * 0.001 << "," << current.time_s
               << "," << current.record_index << ","
               << target.controller_join_delta_ms << ","
               << target.controller.controller_contact_mask << ","
               << target.controller.physical_contact_mask << ","
               << current.live_contact_mask << "," << actual_contact.foot_mask
               << "," << candidate_contact.foot_mask << "," << actual_qacc
               << "," << candidate_qacc << "," << delta_ax << ","
               << actual_residual << "," << snapshot_ctrl_residual << ","
               << formula_residual << "," << candidate_formula_residual
               << ",0,0,0,0,0," << max_snapshot_dq_change << ","
               << max_snapshot_d_target_change << "," << snapshot_stance_legs
               << "," << snapshot_solved_legs << "," << snapshot_invalid_legs
               << "," << dq_cap_limited_legs << "," << d_cap_limited_legs
               << "," << both_limited_legs << "," << unlimited_legs << ","
               << zero_correction_legs << "," << max_baseline_mismatch_norm
               << "," << max_candidate_mismatch_norm << "\n";
      }
    }

    summary_output << "targets," << targets.size() << "\n"
                   << "stance_legs," << stance_legs << "\n"
                   << "solved_legs," << solved_legs << "\n"
                   << "invalid_legs," << invalid_legs << "\n"
                   << "target_join_failures," << target_join_failures << "\n"
                   << "max_snapshot_ctrl_residual_Nm," << max_snapshot_ctrl_residual
                   << "\n"
                   << "max_bridge_formula_residual_Nm," << max_formula_residual
                   << "\n"
                   << "max_actual_replay_residual_mps2," << max_actual_residual
                   << "\n"
                   << "max_candidate_formula_residual_Nm,"
                   << max_candidate_formula_residual << "\n"
                   << "max_dq_change_radps," << max_dq_change << "\n"
                   << "max_d_target_change_Nm," << max_d_target_change << "\n"
                   << "max_swing_dq_change_radps," << max_swing_dq_change << "\n"
                   << "contact_mismatches," << contact_mismatches << "\n"
                   << "candidate_formula_rows," << candidate_formula_rows << "\n";

    const double invalid_fraction = stance_legs > 0
        ? static_cast<double>(invalid_legs) / stance_legs : 0.0;
    std::cerr << "replay_bounded_stance_dq targets=" << targets.size()
              << " stance_legs=" << stance_legs
              << " solved_legs=" << solved_legs
              << " invalid_legs=" << invalid_legs
              << " invalid_fraction=" << invalid_fraction
              << " max_snapshot_ctrl_residual="
              << max_snapshot_ctrl_residual
              << " max_formula_residual=" << max_formula_residual
              << " max_actual_residual=" << max_actual_residual
              << " max_candidate_formula_residual="
              << max_candidate_formula_residual
              << " max_dq_change=" << max_dq_change
              << " max_d_target_change=" << max_d_target_change
              << " contact_mismatches=" << contact_mismatches << "\n";

    mj_deleteData(actual);
    mj_deleteData(candidate);
    mj_deleteModel(model);
    return 0;
  }
  catch (const std::exception &error)
  {
    std::cerr << "replay_bounded_stance_dq: " << error.what() << "\n";
    return 1;
  }
}
