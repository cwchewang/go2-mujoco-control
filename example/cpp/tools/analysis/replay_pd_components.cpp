#define main replay_bridge_atomic_legacy_main
#include "replay_bridge_atomic.cpp"
#undef main

#include <array>
#include <fstream>
#include <iomanip>
#include <map>
#include <sstream>
#include <tuple>
#include <vector>

namespace
{
enum class RemovedComponent
{
  P,
  D,
  PD,
};

struct BranchDefinition
{
  std::string label;
  std::string component;
  std::string scope;
  int motor_index = -1;
  int first_motor = -1;
  int last_motor = -1;
  RemovedComponent removed = RemovedComponent::PD;
};

struct SnapshotEffects
{
  double actual_qacc = 0.0;
  double no_pd_qacc = 0.0;
  int replay_contact_mask = 0;
  std::string phase;
  std::array<double, 4> leg_p{};
  std::array<double, 4> leg_d{};
  std::array<double, 4> leg_pd{};
};

struct MetricKey
{
  std::string kind;
  std::string branch;
  std::string component;
  std::string scope;
  int motor_index = -1;
  std::string stratum_type;
  std::string stratum;

  bool operator<(const MetricKey &other) const
  {
    return std::tie(kind, branch, component, scope, motor_index,
                    stratum_type, stratum) <
        std::tie(other.kind, other.branch, other.component, other.scope,
                 other.motor_index, other.stratum_type, other.stratum);
  }
};

using MetricStore = std::map<MetricKey, std::vector<double>>;

constexpr const char *kMotorLabels[kMotorCount] = {
    "FR_hip", "FR_thigh", "FR_calf",
    "FL_hip", "FL_thigh", "FL_calf",
    "RR_hip", "RR_thigh", "RR_calf",
    "RL_hip", "RL_thigh", "RL_calf"};
constexpr const char *kLegLabels[4] = {"FR", "FL", "RR", "RL"};

std::vector<BranchDefinition> BuildBranches()
{
  std::vector<BranchDefinition> branches;
  branches.push_back({"NO_P", "P", "global", -1, 0, 11,
                      RemovedComponent::P});
  branches.push_back({"NO_D", "D", "global", -1, 0, 11,
                      RemovedComponent::D});
  branches.push_back({"NO_PD", "PD", "global", -1, 0, 11,
                      RemovedComponent::PD});
  for (int leg = 0; leg < 4; ++leg)
  {
    const int first = leg * 3;
    branches.push_back({"NO_P_" + std::string(kLegLabels[leg]), "P", "leg",
                        -1, first, first + 2, RemovedComponent::P});
    branches.push_back({"NO_D_" + std::string(kLegLabels[leg]), "D", "leg",
                        -1, first, first + 2, RemovedComponent::D});
    branches.push_back({"NO_PD_" + std::string(kLegLabels[leg]), "PD", "leg",
                        -1, first, first + 2, RemovedComponent::PD});
  }
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
  {
    branches.push_back({"NO_P_" + std::string(kMotorLabels[motor]), "P",
                        "joint", motor, -1, -1, RemovedComponent::P});
    branches.push_back({"NO_D_" + std::string(kMotorLabels[motor]), "D",
                        "joint", motor, -1, -1, RemovedComponent::D});
    branches.push_back({"NO_PD_" + std::string(kMotorLabels[motor]), "PD",
                        "joint", motor, -1, -1, RemovedComponent::PD});
  }
  return branches;
}

bool Affected(const BranchDefinition &branch, int motor)
{
  if (branch.scope == "joint")
    return motor == branch.motor_index;
  return motor >= branch.first_motor && motor <= branch.last_motor;
}

std::array<double, kMotorCount> ComponentControl(
    const Snapshot &snapshot,
    const std::array<double, kMotorCount> &p,
    const std::array<double, kMotorCount> &d,
    const BranchDefinition &branch)
{
  std::array<double, kMotorCount> control = snapshot.snapshot_ctrl;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
  {
    if (!Affected(branch, motor))
      continue;
    if (branch.removed == RemovedComponent::P ||
        branch.removed == RemovedComponent::PD)
      control[motor] -= p[motor];
    if (branch.removed == RemovedComponent::D ||
        branch.removed == RemovedComponent::PD)
      control[motor] -= d[motor];
  }
  return control;
}

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

void AddMetric(
    MetricStore &store, const MetricKey &key, double value)
{
  store[key].push_back(value);
}

void AddAblationMetrics(
    MetricStore &store, const BranchDefinition &branch,
    const SnapshotEffects &effect, double value)
{
  const MetricKey base{
      "ablation", branch.label, branch.component, branch.scope,
      branch.motor_index, "", ""};
  AddMetric(store, MetricKey{base.kind, base.branch, base.component, base.scope,
                             base.motor_index, "full", "all"}, value);
  AddMetric(store, MetricKey{base.kind, base.branch, base.component, base.scope,
                             base.motor_index, "contact_mask", "mask" +
                                 std::to_string(effect.replay_contact_mask)},
            value);
  AddMetric(store, MetricKey{base.kind, base.branch, base.component, base.scope,
                             base.motor_index, "phase", effect.phase}, value);
}

void AddInteractionMetrics(
    MetricStore &store, const std::string &branch,
    const SnapshotEffects &effect, double value)
{
  const MetricKey base{
      "interaction", branch, "interaction", "global", -1, "", ""};
  AddMetric(store, MetricKey{base.kind, base.branch, base.component, base.scope,
                             base.motor_index, "full", "all"}, value);
  AddMetric(store, MetricKey{base.kind, base.branch, base.component, base.scope,
                             base.motor_index, "contact_mask", "mask" +
                                 std::to_string(effect.replay_contact_mask)},
            value);
  AddMetric(store, MetricKey{base.kind, base.branch, base.component, base.scope,
                             base.motor_index, "phase", effect.phase}, value);
}

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

void WriteMetrics(const MetricStore &store, const std::string &path)
{
  std::filesystem::path output_path(path);
  if (!output_path.parent_path().empty())
    std::filesystem::create_directories(output_path.parent_path());
  std::ofstream output(output_path);
  if (!output)
    throw std::runtime_error("cannot open component metrics output");
  output << std::setprecision(17);
  output << "kind,branch,component,scope,motor_index,stratum_type,stratum,n"
         << ",median_mps2,p05_mps2,p95_mps2,fraction_negative"
         << ",fraction_positive,median_abs_mps2,p95_abs_mps2,small_n\n";
  for (const auto &entry : store)
  {
    const MetricKey &key = entry.first;
    const std::vector<double> &values = entry.second;
    std::vector<double> absolute_values;
    absolute_values.reserve(values.size());
    std::size_t negative = 0;
    std::size_t positive = 0;
    for (double value : values)
    {
      absolute_values.push_back(std::abs(value));
      negative += value < 0.0 ? 1 : 0;
      positive += value > 0.0 ? 1 : 0;
    }
    const double count = static_cast<double>(values.size());
    output << CsvEscape(key.kind) << "," << CsvEscape(key.branch) << ","
           << CsvEscape(key.component) << "," << CsvEscape(key.scope) << ","
           << key.motor_index << "," << CsvEscape(key.stratum_type) << ","
           << CsvEscape(key.stratum) << "," << values.size()
           << "," << Quantile(values, 0.50)
           << "," << Quantile(values, 0.05)
           << "," << Quantile(values, 0.95)
           << "," << static_cast<double>(negative) / count
           << "," << static_cast<double>(positive) / count
           << "," << Quantile(absolute_values, 0.50)
           << "," << Quantile(absolute_values, 0.95)
           << "," << (values.size() < 10 ? 1 : 0) << "\n";
  }
}

}  // namespace

int main(int argc, char **argv)
{
  if (argc != 5)
  {
    std::cerr << "usage: replay_pd_components "
              << "<scene.xml> <snapshots.bin> <diagnostic.csv> "
              << "<components.csv>\n";
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
    std::map<std::int64_t, std::int64_t> target_diagnostic_deltas;
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
      target_diagnostic_deltas.emplace(current.state_tick_ms,
                                       diagnostic_delta_ms);
    }
    if (targets.size() != 552)
      throw std::runtime_error("expected exactly 552 validated target snapshots");

    mjData *actual = mj_makeData(model);
    mjData *branch = mj_makeData(model);
    if (actual == nullptr || branch == nullptr)
      throw std::runtime_error("cannot allocate replay data");

    double max_snapshot_ctrl_residual = 0.0;
    double max_formula_residual = 0.0;
    double max_qacc_residual = 0.0;
    std::vector<SnapshotEffects> effects;
    effects.reserve(targets.size());
    std::vector<double> no_pd_deltas;

    for (const Snapshot *current : targets)
    {
      double ctrl_residual = 0.0;
      double formula_residual = 0.0;
      std::array<double, kMotorCount> p{};
      std::array<double, kMotorCount> d{};
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
      {
        ctrl_residual = std::max(
            ctrl_residual,
            std::abs(current->snapshot_ctrl[motor] -
                     current->bridge.ctrl[motor]));
        p[motor] = current->bridge.kp[motor] *
            (current->bridge.q[motor] - current->bridge.sensor_q[motor]);
        d[motor] = current->bridge.kd[motor] *
            (current->bridge.dq[motor] - current->bridge.sensor_dq[motor]);
        formula_residual = std::max(
            formula_residual,
            std::abs(current->bridge.tau_ff[motor] + p[motor] + d[motor] -
                     current->bridge.ctrl[motor]));
      }
      max_snapshot_ctrl_residual = std::max(
          max_snapshot_ctrl_residual, ctrl_residual);
      max_formula_residual = std::max(max_formula_residual, formula_residual);

      SnapshotEffects effect;
      effect.actual_qacc = RestoreAndForward(
          model, actual, *current, header, current->snapshot_ctrl);
      const double qacc_residual = std::abs(
          effect.actual_qacc - current->live_qacc0);
      max_qacc_residual = std::max(max_qacc_residual, qacc_residual);
      effect.replay_contact_mask = Contacts(
          model, actual, foot_geom_ids).foot_mask;
      effect.no_pd_qacc = RestoreAndForward(
          model, branch, *current, header, current->bridge.tau_ff);
      no_pd_deltas.push_back(effect.no_pd_qacc - effect.actual_qacc);
      const auto diagnostic_it = target_diagnostics.find(current->state_tick_ms);
      if (diagnostic_it == target_diagnostics.end())
        throw std::runtime_error("missing target diagnostic");
      effect.phase = PhaseBin(diagnostic_it->second->active_time_s);
      effects.push_back(std::move(effect));
    }

    constexpr double kCtrlGate = 1.0e-12;
    constexpr double kFormulaGate = 1.0e-10;
    constexpr double kQaccGate = 1.0e-5;
    const double no_pd_median = Quantile(no_pd_deltas, 0.50);
    constexpr double kPriorNoPdMedian = -1.617932;
    constexpr double kNoPdTolerance = 1.0e-6;
    if (max_snapshot_ctrl_residual > kCtrlGate ||
        max_formula_residual > kFormulaGate ||
        max_qacc_residual > kQaccGate ||
        std::abs(no_pd_median - kPriorNoPdMedian) > kNoPdTolerance)
    {
      throw std::runtime_error(
          "decomposition validation gate failed: ctrl=" +
          std::to_string(max_snapshot_ctrl_residual) +
          " formula=" + std::to_string(max_formula_residual) +
          " qacc=" + std::to_string(max_qacc_residual) +
          " no_pd_median=" + std::to_string(no_pd_median));
    }

    const std::vector<BranchDefinition> branches = BuildBranches();
    MetricStore metrics;
    for (std::size_t index = 0; index < targets.size(); ++index)
    {
      const Snapshot &current = *targets[index];
      SnapshotEffects &effect = effects[index];
      std::array<double, kMotorCount> p{};
      std::array<double, kMotorCount> d{};
      for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
      {
        p[motor] = current.bridge.kp[motor] *
            (current.bridge.q[motor] - current.bridge.sensor_q[motor]);
        d[motor] = current.bridge.kd[motor] *
            (current.bridge.dq[motor] - current.bridge.sensor_dq[motor]);
      }

      std::map<std::string, double> deltas;
      for (const BranchDefinition &definition : branches)
      {
        double qacc = 0.0;
        if (definition.label == "NO_PD")
        {
          qacc = effect.no_pd_qacc;
        }
        else
        {
          const auto control = ComponentControl(current, p, d, definition);
          qacc = RestoreAndForward(model, branch, current, header, control);
        }
        const double delta = qacc - effect.actual_qacc;
        deltas.emplace(definition.label, delta);
        AddAblationMetrics(metrics, definition, effect, delta);
        if (definition.scope == "leg")
        {
          const int leg = definition.first_motor / 3;
          if (definition.component == "P")
            effect.leg_p[leg] = delta;
          else if (definition.component == "D")
            effect.leg_d[leg] = delta;
          else
            effect.leg_pd[leg] = delta;
        }
      }

      AddInteractionMetrics(
          metrics, "NO_PD_vs_NO_P_plus_NO_D", effect,
          deltas.at("NO_PD") - deltas.at("NO_P") - deltas.at("NO_D"));
      double sum_leg_p = 0.0;
      double sum_leg_d = 0.0;
      double sum_leg_pd = 0.0;
      for (int leg = 0; leg < 4; ++leg)
      {
        sum_leg_p += effect.leg_p[leg];
        sum_leg_d += effect.leg_d[leg];
        sum_leg_pd += effect.leg_pd[leg];
      }
      AddInteractionMetrics(
          metrics, "NO_P_vs_sum_leg_P", effect,
          deltas.at("NO_P") - sum_leg_p);
      AddInteractionMetrics(
          metrics, "NO_D_vs_sum_leg_D", effect,
          deltas.at("NO_D") - sum_leg_d);
      AddInteractionMetrics(
          metrics, "NO_PD_vs_sum_leg_PD", effect,
          deltas.at("NO_PD") - sum_leg_pd);
    }

    WriteMetrics(metrics, argv[4]);
    std::cerr << "replay_pd_components targets=" << targets.size()
              << " branches=" << branches.size()
              << " max_snapshot_ctrl_residual="
              << max_snapshot_ctrl_residual
              << " max_formula_residual=" << max_formula_residual
              << " max_qacc_residual=" << max_qacc_residual
              << " no_pd_median=" << no_pd_median
              << " no_pd_match=PASS\n";

    mj_deleteData(actual);
    mj_deleteData(branch);
    mj_deleteModel(model);
    return 0;
  }
  catch (const std::exception &error)
  {
    std::cerr << "replay_pd_components: " << error.what() << "\n";
    return 1;
  }
}
