#include <mujoco/mujoco.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

namespace
{
constexpr std::size_t kMotorCount = 12;
constexpr double kTargetStart = 31.90;
constexpr double kTargetEnd = 33.00;
constexpr std::int64_t kMaxContextGapMs = 10;
constexpr char kSnapshotMagic[] = "GO2PDSNP";

struct AtomicBridgeRecord
{
  std::uint64_t bridge_ctrl_seq = 0;
  std::uint32_t motor_count = 0;
  double sim_time_s = 0.0;
  std::array<double, kMotorCount> q{};
  std::array<double, kMotorCount> dq{};
  std::array<double, kMotorCount> kp{};
  std::array<double, kMotorCount> kd{};
  std::array<double, kMotorCount> tau_ff{};
  std::array<double, kMotorCount> sensor_q{};
  std::array<double, kMotorCount> sensor_dq{};
  std::array<double, kMotorCount> ctrl{};
};

struct DiagnosticRow
{
  double active_time_s = std::numeric_limits<double>::quiet_NaN();
  double target_velocity_mps = std::numeric_limits<double>::quiet_NaN();
  double applied_velocity_mps = std::numeric_limits<double>::quiet_NaN();
  double measured_velocity_mps = std::numeric_limits<double>::quiet_NaN();
  double roll_rad = std::numeric_limits<double>::quiet_NaN();
  double pitch_rad = std::numeric_limits<double>::quiet_NaN();
  int physical_contact_mask = 0;
};

struct SnapshotHeader
{
  std::uint32_t version = 0;
  std::uint32_t mujoco_version = 0;
  std::uint32_t mjt_num_bytes = 0;
  std::uint32_t state_sig = 0;
  std::uint32_t state_size = 0;
  std::uint32_t nq = 0;
  std::uint32_t nv = 0;
  std::uint32_t na = 0;
  std::uint32_t nu = 0;
  double time_start_s = 0.0;
  double time_end_s = 0.0;
  double timestep_s = 0.0;
};

struct Snapshot
{
  std::uint64_t record_index = 0;
  std::int64_t state_tick_ms = 0;
  double time_s = 0.0;
  double qvel0 = 0.0;
  double live_qacc0 = 0.0;
  std::int32_t live_ncon = 0;
  std::int32_t live_nefc = 0;
  std::int32_t live_contact_mask = 0;
  std::vector<mjtNum> state;
  AtomicBridgeRecord bridge;
  std::array<double, kMotorCount> snapshot_ctrl{};
  std::uint32_t bridge_seq_step_index = 0;
};

struct ContactSummary
{
  int ncon = 0;
  int nefc = 0;
  int foot_mask = 0;
};

bool ParseDouble(const std::string &text, double &value)
{
  char *end = nullptr;
  const char *begin = text.c_str();
  value = std::strtod(begin, &end);
  return end != begin && *end == '\0' && std::isfinite(value);
}

std::vector<std::string> SplitCsv(const std::string &line)
{
  std::vector<std::string> result;
  std::size_t begin = 0;
  while (true)
  {
    const std::size_t comma = line.find(',', begin);
    if (comma == std::string::npos)
    {
      result.push_back(line.substr(begin));
      return result;
    }
    result.push_back(line.substr(begin, comma - begin));
    begin = comma + 1;
  }
}

bool GetDouble(
    const std::vector<std::string> &fields,
    const std::unordered_map<std::string, std::size_t> &columns,
    const std::string &name,
    double &value)
{
  const auto it = columns.find(name);
  return it != columns.end() &&
      it->second < fields.size() &&
      ParseDouble(fields[it->second], value);
}

bool GetInt(
    const std::vector<std::string> &fields,
    const std::unordered_map<std::string, std::size_t> &columns,
    const std::string &name,
    int &value)
{
  double parsed = 0.0;
  if (!GetDouble(fields, columns, name, parsed))
    return false;
  value = static_cast<int>(std::llround(parsed));
  return true;
}

std::map<std::int64_t, DiagnosticRow> ReadDiagnostics(
    const std::string &path)
{
  std::ifstream input(path);
  if (!input)
    throw std::runtime_error("cannot open diagnostic CSV: " + path);

  std::string line;
  if (!std::getline(input, line))
    throw std::runtime_error("diagnostic CSV is empty");
  if (!line.empty() && line.back() == '\r')
    line.pop_back();
  const std::vector<std::string> header = SplitCsv(line);
  std::unordered_map<std::string, std::size_t> columns;
  for (std::size_t i = 0; i < header.size(); ++i)
    columns.emplace(header[i], i);

  std::map<std::int64_t, DiagnosticRow> rows;
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

    DiagnosticRow row;
    row.active_time_s = active_time;
    GetDouble(fields, columns, "velocity_requested_mps",
              row.target_velocity_mps);
    GetDouble(fields, columns, "velocity_applied_mps",
              row.applied_velocity_mps);
    GetDouble(fields, columns, "velocity_measured_mps",
              row.measured_velocity_mps);
    GetDouble(fields, columns, "roll_rad", row.roll_rad);
    GetDouble(fields, columns, "pitch_rad", row.pitch_rad);
    GetInt(fields, columns, "physical_contact_mask",
           row.physical_contact_mask);

    const std::int64_t tick_ms =
        static_cast<std::int64_t>(std::llround(tick_s * 1000.0));
    if (rows.find(tick_ms) != rows.end())
      throw std::runtime_error(
          "ambiguous diagnostic join: duplicate state tick");
    rows.emplace(tick_ms, row);
  }
  return rows;
}

template <typename T>
bool ReadScalar(std::ifstream &input, T &value)
{
  return static_cast<bool>(input.read(
      reinterpret_cast<char *>(&value),
      static_cast<std::streamsize>(sizeof(T))));
}

template <std::size_t N>
bool ReadArray(
    std::ifstream &input, std::array<double, N> &values)
{
  for (double &value : values)
  {
    if (!ReadScalar(input, value))
      return false;
  }
  return true;
}

bool ReadSnapshotHeader(
    std::ifstream &input, SnapshotHeader &header)
{
  char magic[sizeof(kSnapshotMagic) - 1] = {};
  if (!input.read(magic, sizeof(magic)))
    return false;
  if (!std::equal(std::begin(magic), std::end(magic),
                  std::begin(kSnapshotMagic)))
    throw std::runtime_error("snapshot magic mismatch");
  if (!ReadScalar(input, header.version) ||
      !ReadScalar(input, header.mujoco_version) ||
      !ReadScalar(input, header.mjt_num_bytes) ||
      !ReadScalar(input, header.state_sig) ||
      !ReadScalar(input, header.state_size) ||
      !ReadScalar(input, header.nq) ||
      !ReadScalar(input, header.nv) ||
      !ReadScalar(input, header.na) ||
      !ReadScalar(input, header.nu) ||
      !ReadScalar(input, header.time_start_s) ||
      !ReadScalar(input, header.time_end_s) ||
      !ReadScalar(input, header.timestep_s))
    throw std::runtime_error("truncated snapshot header");
  if (header.version != 2 ||
      header.mjt_num_bytes != sizeof(mjtNum) ||
      header.state_size == 0)
    throw std::runtime_error("unsupported bridge-atomic snapshot header");
  return true;
}

bool ReadSnapshot(
    std::ifstream &input, const SnapshotHeader &header, Snapshot &snapshot)
{
  if (!ReadScalar(input, snapshot.record_index))
    return false;
  if (!ReadScalar(input, snapshot.state_tick_ms) ||
      !ReadScalar(input, snapshot.time_s) ||
      !ReadScalar(input, snapshot.qvel0) ||
      !ReadScalar(input, snapshot.live_qacc0) ||
      !ReadScalar(input, snapshot.live_ncon) ||
      !ReadScalar(input, snapshot.live_nefc) ||
      !ReadScalar(input, snapshot.live_contact_mask))
    throw std::runtime_error("truncated snapshot record");
  std::uint32_t state_size = 0;
  if (!ReadScalar(input, state_size) || state_size != header.state_size)
    throw std::runtime_error("snapshot state size mismatch");
  snapshot.state.resize(header.state_size);
  if (!input.read(
          reinterpret_cast<char *>(snapshot.state.data()),
          static_cast<std::streamsize>(
              snapshot.state.size() * sizeof(mjtNum))))
    throw std::runtime_error("truncated snapshot state");

  if (!ReadScalar(input, snapshot.bridge.bridge_ctrl_seq) ||
      !ReadScalar(input, snapshot.bridge.motor_count) ||
      !ReadScalar(input, snapshot.bridge.sim_time_s) ||
      !ReadArray(input, snapshot.bridge.q) ||
      !ReadArray(input, snapshot.bridge.dq) ||
      !ReadArray(input, snapshot.bridge.kp) ||
      !ReadArray(input, snapshot.bridge.kd) ||
      !ReadArray(input, snapshot.bridge.tau_ff) ||
      !ReadArray(input, snapshot.bridge.sensor_q) ||
      !ReadArray(input, snapshot.bridge.sensor_dq) ||
      !ReadArray(input, snapshot.bridge.ctrl) ||
      !ReadArray(input, snapshot.snapshot_ctrl) ||
      !ReadScalar(input, snapshot.bridge_seq_step_index))
    throw std::runtime_error("truncated bridge-atomic snapshot record");
  return true;
}

ContactSummary Contacts(
    const mjModel *model, const mjData *data,
    const std::array<int, 4> &foot_geom_ids)
{
  ContactSummary result;
  result.ncon = data->ncon;
  result.nefc = data->nefc;
  for (int contact_id = 0; contact_id < data->ncon; ++contact_id)
  {
    const mjContact &contact = data->contact[contact_id];
    if (contact.exclude != 0 || contact.efc_address < 0)
      continue;
    for (std::size_t leg = 0; leg < foot_geom_ids.size(); ++leg)
    {
      const int foot_geom = foot_geom_ids[leg];
      if (foot_geom < 0 ||
          (contact.geom[0] != foot_geom &&
           contact.geom[1] != foot_geom))
        continue;
      const int other_geom =
          contact.geom[0] == foot_geom ? contact.geom[1] : contact.geom[0];
      if (other_geom >= 0 && other_geom < model->ngeom &&
          model->geom_bodyid[other_geom] == 0)
        result.foot_mask |= 1 << static_cast<int>(leg);
    }
  }
  return result;
}

int Popcount(int mask)
{
  int count = 0;
  for (int bit = 0; bit < 4; ++bit)
    count += (mask >> bit) & 1;
  return count;
}

const DiagnosticRow *NearestDiagnostic(
    const std::map<std::int64_t, DiagnosticRow> &rows,
    std::int64_t tick_ms,
    std::int64_t &delta_ms)
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
  return &best->second;
}

template <typename T>
void WriteScalar(std::ofstream &output, const T &value)
{
  output.write(
      reinterpret_cast<const char *>(&value),
      static_cast<std::streamsize>(sizeof(T)));
}

void WriteHeader(std::ofstream &output)
{
  output << "active_relative_time_s,state_tick_s,sim_time_s,snapshot_index"
         << ",bridge_ctrl_seq,bridge_sim_time_s,bridge_seq_step_index"
         << ",bridge_seq_steps_total,diagnostic_tick_delta_ms"
         << ",velocity_target_mps,velocity_applied_mps"
         << ",velocity_measured_mps,velocity_error_measured_minus_applied_mps"
         << ",gait_phase,roll_rad,pitch_rad"
         << ",physical_contact_mask_live,physical_contact_count_live"
         << ",physical_contact_mask_diagnostic"
         << ",live_ncon,live_nefc"
         << ",actual_ncon,actual_nefc,actual_contact_mask"
         << ",cf_ncon,cf_nefc,cf_contact_mask"
         << ",qvel_snapshot0_mps,qacc_live0_mps2"
         << ",qacc_actual0_mps2,qacc_cf0_mps2,delta_ax_mps2"
         << ",snapshot_ctrl_max_abs_Nm,bridge_formula_max_abs_Nm"
         << ",replay_qacc_live_residual_mps2";
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",tau_ff_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",pd_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",ctrl_actual_" << motor;
  for (int motor = 0; motor < static_cast<int>(kMotorCount); ++motor)
    output << ",ctrl_cf_" << motor;
  output << "\n";
}
}  // namespace

int main(int argc, char **argv)
{
  if (argc != 5)
  {
    std::cerr << "usage: replay_bridge_atomic "
              << "<scene.xml> <snapshots.bin> <diagnostic.csv> <output.csv>\n";
    return 2;
  }

  try
  {
    const auto diagnostics = ReadDiagnostics(argv[3]);

    char error[1024] = {};
    mjModel *model = mj_loadXML(argv[1], nullptr, error, sizeof(error));
    if (model == nullptr)
      throw std::runtime_error(
          std::string("cannot load scene: ") + error);

    std::ifstream snapshot_input(argv[2], std::ios::binary);
    if (!snapshot_input)
      throw std::runtime_error("cannot open snapshot file");

    SnapshotHeader header;
    if (!ReadSnapshotHeader(snapshot_input, header))
      throw std::runtime_error("snapshot file is empty");
    if (header.mujoco_version != static_cast<std::uint32_t>(mj_version()) ||
        header.nq != static_cast<std::uint32_t>(model->nq) ||
        header.nv != static_cast<std::uint32_t>(model->nv) ||
        header.na != static_cast<std::uint32_t>(model->na) ||
        header.nu != static_cast<std::uint32_t>(model->nu) ||
        header.state_sig != mjSTATE_INTEGRATION)
      throw std::runtime_error("snapshot/model signature mismatch");

    if (header.nu != kMotorCount)
      throw std::runtime_error("bridge-atomic replay requires 12 actuators");

    std::array<int, 4> foot_geom_ids = {-1, -1, -1, -1};
    const char *foot_names[] = {"FR", "FL", "RR", "RL"};
    for (std::size_t leg = 0; leg < foot_geom_ids.size(); ++leg)
      foot_geom_ids[leg] =
          mj_name2id(model, mjOBJ_GEOM, foot_names[leg]);

    std::vector<Snapshot> snapshots;
    Snapshot snapshot;
    while (ReadSnapshot(snapshot_input, header, snapshot))
      snapshots.push_back(std::move(snapshot));
    if (snapshots.empty())
      throw std::runtime_error("snapshot file contains no records");

    std::map<std::uint64_t, std::uint32_t> sequence_totals;
    std::uint64_t previous_seq = 0;
    std::uint32_t previous_step_index = 0;
    bool have_previous_seq = false;
    for (const Snapshot &current : snapshots)
    {
      const std::uint64_t seq = current.bridge.bridge_ctrl_seq;
      if (seq == 0 || current.bridge.motor_count != header.nu)
        throw std::runtime_error(
            "invalid or unbound atomic bridge record");
      ++sequence_totals[seq];
      if (!have_previous_seq)
      {
        if (current.bridge_seq_step_index != 1)
          throw std::runtime_error("first bridge sequence index is not one");
      }
      else if (seq < previous_seq)
      {
        throw std::runtime_error("bridge_ctrl_seq is not monotonic");
      }
      else if (seq == previous_seq)
      {
        if (current.bridge_seq_step_index != previous_step_index + 1)
          throw std::runtime_error(
              "bridge sequence reuse index is not consecutive");
      }
      else if (current.bridge_seq_step_index != 1)
      {
        throw std::runtime_error(
            "new bridge_ctrl_seq does not start at one");
      }
      previous_seq = seq;
      previous_step_index = current.bridge_seq_step_index;
      have_previous_seq = true;
    }

    std::vector<const Snapshot *> target_snapshots;
    std::map<std::int64_t, int> seen_target_ticks;
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
      if (++seen_target_ticks[current.state_tick_ms] > 1)
        throw std::runtime_error(
            "ambiguous target snapshot: duplicate state tick");
      target_snapshots.push_back(&current);
      target_diagnostics[current.state_tick_ms] = diagnostic;
      target_diagnostic_deltas[current.state_tick_ms] = diagnostic_delta_ms;
    }
    if (target_snapshots.empty())
      throw std::runtime_error("no target snapshots in active window");

    mjData *actual = mj_makeData(model);
    mjData *counterfactual = mj_makeData(model);
    if (actual == nullptr || counterfactual == nullptr)
      throw std::runtime_error("cannot allocate replay data");

    double max_snapshot_ctrl_residual = 0.0;
    double max_formula_residual = 0.0;
    double max_qacc_residual = 0.0;
    for (const Snapshot *current : target_snapshots)
    {
      double snapshot_ctrl_residual = 0.0;
      double formula_residual = 0.0;
      for (std::size_t motor = 0; motor < kMotorCount; ++motor)
      {
        snapshot_ctrl_residual = std::max(
            snapshot_ctrl_residual,
            std::abs(current->snapshot_ctrl[motor] -
                     current->bridge.ctrl[motor]));
        const double formula =
            current->bridge.tau_ff[motor] +
            current->bridge.kp[motor] *
                (current->bridge.q[motor] -
                 current->bridge.sensor_q[motor]) +
            current->bridge.kd[motor] *
                (current->bridge.dq[motor] -
                 current->bridge.sensor_dq[motor]);
        formula_residual = std::max(
            formula_residual,
            std::abs(formula - current->bridge.ctrl[motor]));
      }
      max_snapshot_ctrl_residual = std::max(
          max_snapshot_ctrl_residual, snapshot_ctrl_residual);
      max_formula_residual = std::max(max_formula_residual, formula_residual);

      mj_setState(
          model, actual, current->state.data(), header.state_sig);
      for (std::size_t motor = 0; motor < kMotorCount; ++motor)
        actual->ctrl[motor] = current->snapshot_ctrl[motor];
      mj_forward(model, actual);
      const double qacc_residual =
          std::abs(static_cast<double>(actual->qacc[0]) -
                   current->live_qacc0);
      max_qacc_residual = std::max(max_qacc_residual, qacc_residual);
    }

    constexpr double kCtrlGate = 1.0e-12;
    constexpr double kFormulaGate = 1.0e-10;
    constexpr double kQaccGate = 1.0e-5;
    if (max_snapshot_ctrl_residual > kCtrlGate ||
        max_formula_residual > kFormulaGate ||
        max_qacc_residual > kQaccGate)
    {
      throw std::runtime_error(
          "atomic/replay validation gate failed: max snapshot_ctrl_residual=" +
          std::to_string(max_snapshot_ctrl_residual) +
          " max formula_residual=" + std::to_string(max_formula_residual) +
          " max qacc_residual=" + std::to_string(max_qacc_residual));
    }

    std::filesystem::path output_path(argv[4]);
    if (!output_path.parent_path().empty())
      std::filesystem::create_directories(output_path.parent_path());
    std::ofstream output(output_path);
    if (!output)
      throw std::runtime_error("cannot open replay output");
    output << std::setprecision(17);
    WriteHeader(output);

    for (const Snapshot *current : target_snapshots)
    {
      const DiagnosticRow &diagnostic =
          *target_diagnostics.at(current->state_tick_ms);
      const std::int64_t diagnostic_delta_ms =
          target_diagnostic_deltas.at(current->state_tick_ms);

      mj_setState(
          model, actual, current->state.data(), header.state_sig);
      for (std::size_t motor = 0; motor < kMotorCount; ++motor)
        actual->ctrl[motor] = current->snapshot_ctrl[motor];
      mj_forward(model, actual);

      mj_setState(
          model, counterfactual, current->state.data(), header.state_sig);
      for (std::size_t motor = 0; motor < kMotorCount; ++motor)
        counterfactual->ctrl[motor] = current->bridge.tau_ff[motor];
      mj_forward(model, counterfactual);

      double snapshot_ctrl_residual = 0.0;
      double formula_residual = 0.0;
      for (std::size_t motor = 0; motor < kMotorCount; ++motor)
      {
        snapshot_ctrl_residual = std::max(
            snapshot_ctrl_residual,
            std::abs(current->snapshot_ctrl[motor] -
                     current->bridge.ctrl[motor]));
        const double formula =
            current->bridge.tau_ff[motor] +
            current->bridge.kp[motor] *
                (current->bridge.q[motor] -
                 current->bridge.sensor_q[motor]) +
            current->bridge.kd[motor] *
                (current->bridge.dq[motor] -
                 current->bridge.sensor_dq[motor]);
        formula_residual = std::max(
            formula_residual,
            std::abs(formula - current->bridge.ctrl[motor]));
      }
      const ContactSummary actual_contact =
          Contacts(model, actual, foot_geom_ids);
      const ContactSummary cf_contact =
          Contacts(model, counterfactual, foot_geom_ids);
      const double qacc_residual =
          std::abs(static_cast<double>(actual->qacc[0]) -
                   current->live_qacc0);
      const double delta_ax =
          static_cast<double>(counterfactual->qacc[0]) -
          static_cast<double>(actual->qacc[0]);
      const double active_phase = std::fmod(
          diagnostic.active_time_s / 0.14, 1.0);
      const double gait_phase = active_phase < 0.0
          ? active_phase + 1.0 : active_phase;

      output << diagnostic.active_time_s
             << "," << current->state_tick_ms * 0.001
             << "," << current->time_s
             << "," << current->record_index
             << "," << current->bridge.bridge_ctrl_seq
             << "," << current->bridge.sim_time_s
             << "," << current->bridge_seq_step_index
             << "," << sequence_totals.at(current->bridge.bridge_ctrl_seq)
             << "," << diagnostic_delta_ms
             << "," << diagnostic.target_velocity_mps
             << "," << diagnostic.applied_velocity_mps
             << "," << diagnostic.measured_velocity_mps
             << "," << (diagnostic.measured_velocity_mps -
                         diagnostic.applied_velocity_mps)
             << "," << gait_phase
             << "," << diagnostic.roll_rad
             << "," << diagnostic.pitch_rad
             << "," << current->live_contact_mask
             << "," << Popcount(current->live_contact_mask)
             << "," << diagnostic.physical_contact_mask
             << "," << current->live_ncon
             << "," << current->live_nefc
             << "," << actual_contact.ncon
             << "," << actual_contact.nefc
             << "," << actual_contact.foot_mask
             << "," << cf_contact.ncon
             << "," << cf_contact.nefc
             << "," << cf_contact.foot_mask
             << "," << current->qvel0
             << "," << current->live_qacc0
             << "," << actual->qacc[0]
             << "," << counterfactual->qacc[0]
             << "," << delta_ax
             << "," << snapshot_ctrl_residual
             << "," << formula_residual
             << "," << qacc_residual;
      for (double value : current->bridge.tau_ff)
        output << "," << value;
      for (std::size_t motor = 0; motor < kMotorCount; ++motor)
        output << "," << (current->bridge.ctrl[motor] -
                          current->bridge.tau_ff[motor]);
      for (double value : current->bridge.ctrl)
        output << "," << value;
      for (double value : current->bridge.tau_ff)
        output << "," << value;
      output << "\n";
    }

    output.flush();
    std::cerr << "bridge_atomic raw_snapshots=" << snapshots.size()
              << " target_snapshots=" << target_snapshots.size()
              << " max_snapshot_ctrl_residual="
              << max_snapshot_ctrl_residual
              << " max_formula_residual=" << max_formula_residual
              << " max_qacc_residual=" << max_qacc_residual << "\n";

    mj_deleteData(actual);
    mj_deleteData(counterfactual);
    mj_deleteModel(model);
    return 0;
  }
  catch (const std::exception &error)
  {
    std::cerr << "replay_bridge_atomic: " << error.what() << "\n";
    return 1;
  }
}
