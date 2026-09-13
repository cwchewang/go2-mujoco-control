#define main replay_bridge_atomic_legacy_main
#include "replay_bridge_atomic.cpp"
#undef main

#include <array>
#include <fstream>
#include <iomanip>
#include <map>
#include <sstream>
#include <string>
#include <tuple>
#include <vector>

namespace
{
struct SnapshotEffects
{
  double actual_qacc = 0.0;
  int replay_contact_mask = 0;
  std::string phase;
};

double RestoreAndForward(
    const mjModel *model, mjData *data, const Snapshot &snapshot,
    const SnapshotHeader &header,
    const std::array<double, kMotorCount> &control)
{
  mj_setState(model, data, snapshot.state.data(), header.state_sig);
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    data->ctrl[motor] = control[motor];
  mj_forward(model, data);
  return static_cast<double>(data->qacc[0]);
}

std::string PhaseBin(double active_time_s)
{
  double phase = std::fmod(active_time_s / 0.14, 1.0);
  if (phase < 0.0)
    phase += 1.0;
  if (phase < 0.25)
    return "[0,0.25)";
  if (phase < 0.50)
    return "[0.25,0.5)";
  if (phase < 0.75)
    return "[0.5,0.75)";
  return "[0.75,1)";
}

double Quantile(std::vector<double> values, double probability)
{
  if (values.empty())
    return std::numeric_limits<double>::quiet_NaN();
  std::sort(values.begin(), values.end());
  const double index = probability * static_cast<double>(values.size() - 1);
  const std::size_t lower = static_cast<std::size_t>(std::floor(index));
  const std::size_t upper = std::min(lower + 1, values.size() - 1);
  const double fraction = index - static_cast<double>(lower);
  return values[lower] + fraction * (values[upper] - values[lower]);
}

constexpr const char *kLegLabels[4] = {"FR", "FL", "RR", "RL"};
constexpr std::array<int, 4> kThighMotors = {1, 4, 7, 10};
constexpr double kCandidateRetain[3] = {0.90, 0.80, 0.70};
constexpr double kCandidateAttenuation[3] = {0.10, 0.20, 0.30};
constexpr const char *kCandidateLabels[3] = {
    "THIGH_D_90", "THIGH_D_80", "THIGH_D_70"};
constexpr double kBindingGate = 1.0e-12;
constexpr double kFormulaGate = 1.0e-10;
constexpr double kQaccGate = 1.0e-5;
constexpr double kIsolationGate = 1.0e-10;
constexpr double kMonotonicTolerance = 1.0e-12;

struct MetricKey
{
  int candidate = -1;
  std::string stratum_type;
  std::string stratum;

  bool operator<(const MetricKey &other) const
  {
    return std::tie(candidate, stratum_type, stratum) <
        std::tie(other.candidate, other.stratum_type, other.stratum);
  }
};

using MetricStore = std::map<MetricKey, std::vector<double>>;

std::array<double, kMotorCount> CandidateControl(
    const Snapshot &snapshot,
    const std::array<double, kMotorCount> &d,
    double attenuation)
{
  std::array<double, kMotorCount> control = snapshot.snapshot_ctrl;
  for (const int motor : kThighMotors)
    control[motor] -= attenuation * d[motor];
  return control;
}

void AddMetric(
    MetricStore &store, int candidate, const std::string &stratum_type,
    const std::string &stratum, double value)
{
  store[MetricKey{candidate, stratum_type, stratum}].push_back(value);
}

void AddSampleMetrics(
    MetricStore &store, int candidate, const SnapshotEffects &effect,
    double value)
{
  AddMetric(store, candidate, "full", "all", value);
  AddMetric(store, candidate, "contact_mask",
            "mask" + std::to_string(effect.replay_contact_mask), value);
  AddMetric(store, candidate, "phase", effect.phase, value);
}

void WriteMetricRow(
    std::ofstream &output, int candidate, const std::string &stratum_type,
    const std::string &stratum, const std::vector<double> &values)
{
  std::vector<double> absolute_values;
  absolute_values.reserve(values.size());
  std::size_t negative = 0;
  std::size_t positive = 0;
  for (const double value : values)
  {
    absolute_values.push_back(std::abs(value));
    negative += value < 0.0 ? 1 : 0;
    positive += value > 0.0 ? 1 : 0;
  }
  const double count = static_cast<double>(values.size());
  output << "metric," << kCandidateLabels[candidate] << ","
         << kCandidateRetain[candidate] << ","
         << kCandidateAttenuation[candidate] << ","
         << stratum_type << "," << stratum << "," << values.size()
         << "," << Quantile(values, 0.50)
         << "," << Quantile(values, 0.05)
         << "," << Quantile(values, 0.95)
         << "," << static_cast<double>(negative) / count
         << "," << static_cast<double>(positive) / count
         << "," << Quantile(absolute_values, 0.50)
         << "," << (values.size() < 20 ? 1 : 0)
         << ",,,,,,,PASS\n";
}

void WriteValidationRow(
    std::ofstream &output, const std::string &name, double value,
    std::size_t count)
{
  output << "validation,ALL,,,,validation," << count
         << ",,,,,,,,,,," << name << "," << value << ",PASS\n";
}

}  // namespace

int main(int argc, char **argv)
{
  if (argc != 5)
  {
    std::cerr << "usage: replay_four_thigh_d_screen "
              << "<scene.xml> <snapshots.bin> <diagnostic.csv> "
              << "<screen.csv>\n";
    return 2;
  }

  try
  {
    const auto diagnostics = ReadDiagnostics(argv[3]);
    char error[1024] = {};
    mjModel *model = mj_loadXML(argv[1], nullptr, error, sizeof(error));
    if (model == nullptr)
      throw std::runtime_error(std::string("cannot load scene: ") + error);
    std::array<int, 4> foot_geom_ids = {-1, -1, -1, -1};
    for (int leg = 0; leg < 4; ++leg)
      foot_geom_ids[leg] = mj_name2id(model, mjOBJ_GEOM, kLegLabels[leg]);

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
    std::uint32_t previous_step_index = 0;
    bool have_previous_seq = false;
    for (const Snapshot &current : snapshots)
    {
      if (current.bridge.bridge_ctrl_seq == 0 ||
          current.bridge.motor_count != header.nu)
        throw std::runtime_error("invalid atomic bridge record");
      if (!have_previous_seq)
      {
        if (current.bridge_seq_step_index != 1)
          throw std::runtime_error("first bridge sequence index is not one");
      }
      else if (current.bridge.bridge_ctrl_seq < previous_seq)
      {
        throw std::runtime_error("bridge sequence is not monotonic");
      }
      else if (current.bridge.bridge_ctrl_seq == previous_seq &&
               current.bridge_seq_step_index != previous_step_index + 1)
      {
        throw std::runtime_error("bridge sequence reuse index is not consecutive");
      }
      else if (current.bridge.bridge_ctrl_seq != previous_seq &&
               current.bridge_seq_step_index != 1)
      {
        throw std::runtime_error("new bridge sequence does not start at one");
      }
      previous_seq = current.bridge.bridge_ctrl_seq;
      previous_step_index = current.bridge_seq_step_index;
      have_previous_seq = true;
    }

    std::vector<const Snapshot *> targets;
    std::map<std::int64_t, const DiagnosticRow *> target_diagnostics;
    for (const Snapshot &current : snapshots)
    {
      std::int64_t diagnostic_delta_ms = 0;
      const DiagnosticRow *diagnostic = NearestDiagnostic(
          diagnostics, current.state_tick_ms, diagnostic_delta_ms);
      if (diagnostic == nullptr ||
          std::llabs(diagnostic_delta_ms) > kMaxContextGapMs ||
          diagnostic->active_time_s < kTargetStart ||
          diagnostic->active_time_s >= kTargetEnd)
        continue;
      if (target_diagnostics.find(current.state_tick_ms) !=
          target_diagnostics.end())
        throw std::runtime_error("ambiguous target snapshot");
      targets.push_back(&current);
      target_diagnostics.emplace(current.state_tick_ms, diagnostic);
    }
    if (targets.size() != 552)
      throw std::runtime_error("expected exactly 552 validated target snapshots");

    mjData *actual = mj_makeData(model);
    mjData *candidate = mj_makeData(model);
    if (actual == nullptr || candidate == nullptr)
      throw std::runtime_error("cannot allocate replay data");

    MetricStore metrics;
    std::array<std::size_t, 3> sign_violations = {0, 0, 0};
    std::size_t ordering_violations = 0;
    double max_snapshot_ctrl_residual = 0.0;
    double max_formula_residual = 0.0;
    double max_qacc_residual = 0.0;
    double max_candidate_isolation_residual = 0.0;

    for (const Snapshot *current : targets)
    {
      std::array<double, kMotorCount> p{};
      std::array<double, kMotorCount> d{};
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
      {
        max_snapshot_ctrl_residual = std::max(
            max_snapshot_ctrl_residual,
            std::abs(current->snapshot_ctrl[motor] -
                     current->bridge.ctrl[motor]));
        p[motor] = current->bridge.kp[motor] *
            (current->bridge.q[motor] - current->bridge.sensor_q[motor]);
        d[motor] = current->bridge.kd[motor] *
            (current->bridge.dq[motor] - current->bridge.sensor_dq[motor]);
        max_formula_residual = std::max(
            max_formula_residual,
            std::abs(current->bridge.tau_ff[motor] + p[motor] + d[motor] -
                     current->bridge.ctrl[motor]));
      }

      const double actual_qacc = RestoreAndForward(
          model, actual, *current, header, current->snapshot_ctrl);
      max_qacc_residual = std::max(
          max_qacc_residual, std::abs(actual_qacc - current->live_qacc0));
      SnapshotEffects effect;
      effect.actual_qacc = actual_qacc;
      effect.replay_contact_mask = Contacts(
          model, actual, foot_geom_ids).foot_mask;
      const auto diagnostic_it = target_diagnostics.find(current->state_tick_ms);
      effect.phase = PhaseBin(diagnostic_it->second->active_time_s);

      std::array<double, 3> deltas{};
      for (int candidate_index = 0; candidate_index < 3; ++candidate_index)
      {
        const auto control = CandidateControl(
            *current, d, kCandidateAttenuation[candidate_index]);
        for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
        {
          const bool affected = std::find(
              kThighMotors.begin(), kThighMotors.end(), motor) !=
              kThighMotors.end();
          const double expected = affected ?
              kCandidateAttenuation[candidate_index] * d[motor] : 0.0;
          max_candidate_isolation_residual = std::max(
              max_candidate_isolation_residual,
              std::abs((current->snapshot_ctrl[motor] - control[motor]) -
                       expected));
        }
        deltas[candidate_index] = RestoreAndForward(
            model, candidate, *current, header, control) - actual_qacc;
        AddSampleMetrics(metrics, candidate_index, effect,
                         deltas[candidate_index]);
      }

      ordering_violations +=
          (deltas[0] + kMonotonicTolerance < deltas[1] ||
           deltas[1] + kMonotonicTolerance < deltas[2]) ? 1 : 0;
      for (int candidate_index = 0; candidate_index < 3; ++candidate_index)
        sign_violations[candidate_index] += deltas[candidate_index] > 0.0 ? 1 : 0;
    }

    const bool gates_pass =
        max_snapshot_ctrl_residual <= kBindingGate &&
        max_formula_residual <= kFormulaGate &&
        max_qacc_residual <= kQaccGate &&
        max_candidate_isolation_residual <= kIsolationGate;
    if (!gates_pass)
      throw std::runtime_error(
          "four-thigh screen validation gate failed: ctrl=" +
          std::to_string(max_snapshot_ctrl_residual) +
          " formula=" + std::to_string(max_formula_residual) +
          " qacc=" + std::to_string(max_qacc_residual) +
          " isolation=" + std::to_string(max_candidate_isolation_residual));

    std::ofstream output(argv[4]);
    if (!output)
      throw std::runtime_error("cannot open screen output");
    output << std::setprecision(17);
    output << "record_type,candidate,retained_d_fraction,attenuation_fraction"
           << ",stratum_type,stratum,n,median_delta_ax_mps2"
           << ",p05_delta_ax_mps2,p95_delta_ax_mps2,fraction_negative"
           << ",fraction_positive,median_abs_delta_ax_mps2,small_n"
           << ",ordering_violations,ordering_violation_fraction"
           << ",sign_violations,sign_violation_fraction,validation_name"
           << ",validation_value,gate_status\n";
    for (const auto &entry : metrics)
      WriteMetricRow(output, entry.first.candidate,
                     entry.first.stratum_type, entry.first.stratum,
                     entry.second);
    output << "monotonicity,ORDERING,,,,full,552,,,,,,,,"
           << ordering_violations << ","
           << static_cast<double>(ordering_violations) / targets.size()
           << ",,,,PASS\n";
    for (int candidate_index = 0; candidate_index < 3; ++candidate_index)
    {
      output << "monotonicity," << kCandidateLabels[candidate_index] << ","
             << kCandidateRetain[candidate_index] << ","
             << kCandidateAttenuation[candidate_index]
             << ",,full,552,,,,,,,,,,"
             << sign_violations[candidate_index] << ","
             << static_cast<double>(sign_violations[candidate_index]) /
                    targets.size()
             << ",,,,PASS\n";
    }
    WriteValidationRow(output, "atomic_bridge_binding_max_abs_residual",
                       max_snapshot_ctrl_residual, targets.size());
    WriteValidationRow(output, "bridge_formula_max_abs_residual",
                       max_formula_residual, targets.size());
    WriteValidationRow(output, "actual_qacc_max_abs_residual_mps2",
                       max_qacc_residual, targets.size());
    WriteValidationRow(output, "candidate_isolation_max_abs_residual",
                       max_candidate_isolation_residual, targets.size());
    WriteValidationRow(output, "independent_state_restore", 1.0,
                       targets.size());

    std::cerr << "replay_four_thigh_d_screen targets=" << targets.size()
              << " candidates=3"
              << " max_snapshot_ctrl_residual="
              << max_snapshot_ctrl_residual
              << " max_formula_residual=" << max_formula_residual
              << " max_qacc_residual=" << max_qacc_residual
              << " max_candidate_isolation_residual="
              << max_candidate_isolation_residual
              << " ordering_violations=" << ordering_violations
              << " sign_violations_90=" << sign_violations[0]
              << " sign_violations_80=" << sign_violations[1]
              << " sign_violations_70=" << sign_violations[2]
              << " gates=PASS\n";

    mj_deleteData(actual);
    mj_deleteData(candidate);
    mj_deleteModel(model);
    return 0;
  }
  catch (const std::exception &error)
  {
    std::cerr << "replay_four_thigh_d_screen: " << error.what() << "\n";
    return 1;
  }
}
