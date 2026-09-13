#include <mujoco/mujoco.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace
{
constexpr int kMotorCount = 12;
constexpr double kTargetStart = 31.90;
constexpr double kTargetEnd = 33.00;
constexpr char kSnapshotMagic[] = "GO2PDSNP";

struct ClosureRow
{
  double active_time_s = std::numeric_limits<double>::quiet_NaN();
  double target_velocity_mps = std::numeric_limits<double>::quiet_NaN();
  double applied_velocity_mps = std::numeric_limits<double>::quiet_NaN();
  double measured_velocity_mps = std::numeric_limits<double>::quiet_NaN();
  double roll_rad = std::numeric_limits<double>::quiet_NaN();
  double pitch_rad = std::numeric_limits<double>::quiet_NaN();
  int controller_contact_mask = 0;
  int physical_contact_mask = 0;
  std::vector<double> q_des;
  std::vector<double> dq_des;
  std::vector<double> kp;
  std::vector<double> kd;
  std::vector<double> tau_ff;

  ClosureRow() :
      q_des(kMotorCount), dq_des(kMotorCount), kp(kMotorCount),
      kd(kMotorCount), tau_ff(kMotorCount) {}
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

std::map<std::int64_t, ClosureRow> ReadClosure(
    const std::string &path, std::set<std::int64_t> &duplicate_ticks)
{
  std::ifstream input(path);
  if (!input)
    throw std::runtime_error("cannot open closure CSV: " + path);

  std::string line;
  if (!std::getline(input, line))
    throw std::runtime_error("closure CSV is empty");
  const std::vector<std::string> header = SplitCsv(line);
  std::unordered_map<std::string, std::size_t> columns;
  for (std::size_t i = 0; i < header.size(); ++i)
    columns.emplace(header[i], i);

  std::map<std::int64_t, ClosureRow> rows;
  while (std::getline(input, line))
  {
    if (line.empty())
      continue;
    const std::vector<std::string> fields = SplitCsv(line);
    double active_time = 0.0;
    double tick_s = 0.0;
    if (!GetDouble(fields, columns, "active_relative_time_s", active_time) ||
        !GetDouble(fields, columns, "state_tick_s", tick_s))
      continue;
    ClosureRow row;
    row.active_time_s = active_time;
    GetDouble(fields, columns, "velocity_requested_mps",
              row.target_velocity_mps);
    GetDouble(fields, columns, "velocity_applied_mps",
              row.applied_velocity_mps);
    GetDouble(fields, columns, "velocity_measured_mps",
              row.measured_velocity_mps);
    GetDouble(fields, columns, "roll_rad", row.roll_rad);
    GetDouble(fields, columns, "pitch_rad", row.pitch_rad);
    GetInt(fields, columns, "solver_contact_mask",
           row.controller_contact_mask);
    GetInt(fields, columns, "physical_contact_mask",
           row.physical_contact_mask);
    for (int motor = 0; motor < kMotorCount; ++motor)
    {
      const std::string prefix = "motor_" + std::to_string(motor) + "_";
      GetDouble(fields, columns, prefix + "q_des", row.q_des[motor]);
      GetDouble(fields, columns, prefix + "dq_des", row.dq_des[motor]);
      GetDouble(fields, columns, prefix + "kp", row.kp[motor]);
      GetDouble(fields, columns, prefix + "kd", row.kd[motor]);
      GetDouble(fields, columns, prefix + "tau_ff", row.tau_ff[motor]);
    }
    const std::int64_t tick_ms =
        static_cast<std::int64_t>(std::llround(tick_s * 1000.0));
    if (rows.find(tick_ms) != rows.end())
      duplicate_ticks.insert(tick_ms);
    else
      rows.emplace(tick_ms, std::move(row));
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
  if (header.version != 1 ||
      header.mjt_num_bytes != sizeof(mjtNum) ||
      header.state_size == 0)
    throw std::runtime_error("unsupported snapshot header");
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
  return true;
}

ContactSummary Contacts(
    const mjModel *model, const mjData *data,
    const std::vector<int> &foot_geom_ids)
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

void WriteHeader(std::ofstream &output)
{
  output << "active_relative_time_s,state_tick_s,sim_time_s,snapshot_index"
         << ",velocity_target_mps,velocity_applied_mps,velocity_measured_mps"
         << ",gait_phase,roll_rad,pitch_rad"
         << ",physical_contact_mask_live,physical_contact_count_live"
         << ",controller_contact_mask,physical_contact_mask_controller"
         << ",ncon_live,nefc_live"
         << ",ncon_actual,nefc_actual,physical_contact_mask_actual"
         << ",ncon_cf,nefc_cf,physical_contact_mask_cf"
         << ",qvel_snapshot0_mps,qacc_live0_mps2"
         << ",qacc_actual0_mps2,qacc_cf0_mps2,delta_ax_mps2"
         << ",replay_qacc_live_residual_mps2,ctrl_reconstruction_max_abs_Nm";
  for (int motor = 0; motor < kMotorCount; ++motor)
    output << ",tau_ff_" << motor;
  for (int motor = 0; motor < kMotorCount; ++motor)
    output << ",pd_" << motor;
  for (int motor = 0; motor < kMotorCount; ++motor)
    output << ",ctrl_live_" << motor;
  for (int motor = 0; motor < kMotorCount; ++motor)
    output << ",ctrl_reconstructed_" << motor;
  for (int motor = 0; motor < kMotorCount; ++motor)
    output << ",ctrl_cf_" << motor;
  output << "\n";
}
}  // namespace

int main(int argc, char **argv)
{
  if (argc != 5)
  {
    std::cerr << "usage: replay_pd_counterfactual "
              << "<scene.xml> <snapshots.bin> <closure.csv> <output.csv>\n";
    return 2;
  }

  try
  {
    std::set<std::int64_t> duplicate_closure_ticks;
    const auto closure = ReadClosure(argv[3], duplicate_closure_ticks);
    if (!duplicate_closure_ticks.empty())
      throw std::runtime_error(
          "ambiguous closure join: duplicate state ticks");

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
        header.nu != static_cast<std::uint32_t>(model->nu))
      throw std::runtime_error("snapshot/model signature mismatch");
    if (header.state_sig != mjSTATE_INTEGRATION)
      throw std::runtime_error("snapshot state signature is not integration");

    std::vector<int> foot_geom_ids(4, -1);
    for (int leg = 0; leg < 4; ++leg)
    {
      const char *names[] = {"FR", "FL", "RR", "RL"};
      foot_geom_ids[leg] = mj_name2id(model, mjOBJ_GEOM, names[leg]);
    }

    mjData *actual = mj_makeData(model);
    mjData *counterfactual = mj_makeData(model);
    if (actual == nullptr || counterfactual == nullptr)
      throw std::runtime_error("cannot allocate replay data");

    std::ofstream output(argv[4]);
    if (!output)
      throw std::runtime_error("cannot open replay output");
    output << std::setprecision(17);
    WriteHeader(output);

    std::map<std::int64_t, int> seen_snapshot_ticks;
    std::uint64_t raw_records = 0;
    std::uint64_t joined_records = 0;
    std::uint64_t unmatched_records = 0;
    std::uint64_t duplicate_snapshot_ticks = 0;
    double max_qacc_residual = 0.0;
    double max_ctrl_residual = 0.0;

    Snapshot snapshot;
    while (ReadSnapshot(snapshot_input, header, snapshot))
    {
      ++raw_records;
      const auto join = closure.find(snapshot.state_tick_ms);
      if (join == closure.end() ||
          join->second.active_time_s < kTargetStart ||
          join->second.active_time_s >= kTargetEnd)
      {
        if (join == closure.end())
          ++unmatched_records;
        continue;
      }
      if (++seen_snapshot_ticks[snapshot.state_tick_ms] > 1)
        ++duplicate_snapshot_ticks;

      const ClosureRow &row = join->second;
      mj_setState(
          model, actual, snapshot.state.data(), header.state_sig);
      mj_forward(model, actual);
      mj_setState(
          model, counterfactual, snapshot.state.data(), header.state_sig);
      for (int motor = 0; motor < kMotorCount; ++motor)
        counterfactual->ctrl[motor] =
            static_cast<mjtNum>(row.tau_ff[motor]);
      mj_forward(model, counterfactual);

      const double period_s = header.timestep_s > 0.0
          ? 0.14 : 0.14;
      const double gait_phase = std::fmod(
          row.active_time_s / period_s, 1.0) < 0.0
          ? std::fmod(row.active_time_s / period_s, 1.0) + 1.0
          : std::fmod(row.active_time_s / period_s, 1.0);
      std::vector<double> reconstructed(kMotorCount);
      double max_ctrl_error = 0.0;
      for (int motor = 0; motor < kMotorCount; ++motor)
      {
        const double q_state = actual->sensordata[motor];
        const double dq_state = actual->sensordata[motor + model->nu];
        reconstructed[motor] =
            row.tau_ff[motor] +
            row.kp[motor] * (row.q_des[motor] - q_state) +
            row.kd[motor] * (row.dq_des[motor] - dq_state);
        max_ctrl_error = std::max(
            max_ctrl_error,
            std::abs(reconstructed[motor] -
                     static_cast<double>(actual->ctrl[motor])));
      }
      const ContactSummary actual_contact =
          Contacts(model, actual, foot_geom_ids);
      const ContactSummary cf_contact =
          Contacts(model, counterfactual, foot_geom_ids);
      const double qacc_residual =
          std::abs(static_cast<double>(actual->qacc[0]) -
                   snapshot.live_qacc0);
      max_qacc_residual = std::max(max_qacc_residual, qacc_residual);
      max_ctrl_residual = std::max(max_ctrl_residual, max_ctrl_error);
      output << row.active_time_s << "," << snapshot.state_tick_ms * 0.001
             << "," << snapshot.time_s << "," << snapshot.record_index
             << "," << row.target_velocity_mps
             << "," << row.applied_velocity_mps
             << "," << row.measured_velocity_mps
             << "," << gait_phase
             << "," << row.roll_rad << "," << row.pitch_rad
             << "," << snapshot.live_contact_mask
             << "," << Popcount(snapshot.live_contact_mask)
             << "," << row.controller_contact_mask
             << "," << row.physical_contact_mask
             << "," << snapshot.live_ncon << "," << snapshot.live_nefc
             << "," << actual_contact.ncon << "," << actual_contact.nefc
             << "," << actual_contact.foot_mask
             << "," << cf_contact.ncon << "," << cf_contact.nefc
             << "," << cf_contact.foot_mask
             << "," << snapshot.qvel0 << "," << snapshot.live_qacc0
             << "," << actual->qacc[0] << "," << counterfactual->qacc[0]
             << "," << (static_cast<double>(counterfactual->qacc[0]) -
                         static_cast<double>(actual->qacc[0]))
             << "," << qacc_residual << "," << max_ctrl_error;
      for (double value : row.tau_ff)
        output << "," << value;
      for (int motor = 0; motor < kMotorCount; ++motor)
        output << "," << reconstructed[motor] - row.tau_ff[motor];
      for (int motor = 0; motor < kMotorCount; ++motor)
        output << "," << actual->ctrl[motor];
      for (double value : reconstructed)
        output << "," << value;
      for (int motor = 0; motor < kMotorCount; ++motor)
        output << "," << counterfactual->ctrl[motor];
      output << "\n";
      ++joined_records;
    }

    std::cerr << "replay raw_records=" << raw_records
              << " joined_records=" << joined_records
              << " unmatched_records=" << unmatched_records
              << " duplicate_snapshot_ticks=" << duplicate_snapshot_ticks
              << " max_qacc_residual=" << max_qacc_residual
              << " max_ctrl_residual=" << max_ctrl_residual << "\n";
    if (joined_records == 0 || duplicate_snapshot_ticks != 0)
      throw std::runtime_error(
          "replay join did not yield one unique snapshot per state tick");
    output.flush();
    mj_deleteData(actual);
    mj_deleteData(counterfactual);
    mj_deleteModel(model);
    return 0;
  }
  catch (const std::exception &error)
  {
    std::cerr << "replay_pd_counterfactual: " << error.what() << "\n";
    return 1;
  }
}
