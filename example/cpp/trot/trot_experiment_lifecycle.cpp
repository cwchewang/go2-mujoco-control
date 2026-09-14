#include "trot_experiment.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <thread>

#include "contact_wrench_projected_allocator.h"
#include "contact_state_filter.h"
#include "go2_contact_torque_mapping.h"
#include "go2_inverse_kinematics.h"
#include "motion_frame_utils.h"

using namespace unitree::common;
using namespace unitree::robot;
using namespace go2_trot;

// --- TrotExperiment::InitLowCmd ---
void TrotExperiment::WriteBoundaryTraceRow(
    const std::array<std::string, 22> &row)
{
    if (!boundary_trace_enabled_)
        return;
    std::lock_guard<std::mutex> lock(boundary_trace_mutex_);
    if (!boundary_trace_csv_)
        return;
    for (std::size_t i = 0; i < row.size(); ++i)
    {
        if (i != 0) boundary_trace_csv_ << ',';
        boundary_trace_csv_ << row[i];
    }
    boundary_trace_csv_ << '\n';
    boundary_trace_csv_.flush();
}

void TrotExperiment::RecordBoundaryLowReceipt(
    const unitree_go::msg::dds_::LowState_ &message)
{
    const auto payload = phase1_boundary_trace::CanonicalLowState(message);
    const std::string hash = phase1_boundary_trace::Hash(payload);
    std::uint64_t sequence = 0;
    bool have_high_state = false;
    {
        std::lock_guard<std::mutex> lock(state_mutex_);
        low_state_ = message;
        have_low_state_ = true;
        sequence = ++boundary_low_receipt_seq_;
        have_high_state = have_high_state_;
    }
    if (!boundary_trace_enabled_ ||
        !phase1_boundary_trace::InWindow(message.tick()))
        return;
    std::array<std::string, 22> row{};
    row[0] = "controller_receipt_low";
    row[1] = std::to_string(message.tick());
    row[3] = std::to_string(sequence);
    row[4] = hash;
    row[11] = std::to_string(sequence);
    row[15] = "1";
    row[16] = have_high_state ? "1" : "0";
    row[19] = phase1_boundary_trace::Hex(payload);
    WriteBoundaryTraceRow(row);
}

void TrotExperiment::RecordBoundaryHighReceipt(
    const unitree_go::msg::dds_::SportModeState_ &message)
{
    const auto payload = phase1_boundary_trace::CanonicalHighState(message);
    const std::string hash = phase1_boundary_trace::Hash(payload);
    std::uint64_t sequence = 0;
    std::uint32_t low_tick = 0;
    bool have_low_state = false;
    {
        std::lock_guard<std::mutex> lock(state_mutex_);
        high_state_ = message;
        have_high_state_ = true;
        sequence = ++boundary_high_receipt_seq_;
        have_low_state = have_low_state_;
        if (have_low_state)
            low_tick = low_state_.tick();
    }
    if (!boundary_trace_enabled_ ||
        !phase1_boundary_trace::InWindow(low_tick))
        return;
    std::array<std::string, 22> row{};
    row[0] = "controller_receipt_high";
    row[1] = std::to_string(low_tick);
    row[3] = std::to_string(sequence);
    row[5] = hash;
    row[12] = std::to_string(sequence);
    row[15] = have_low_state ? "1" : "0";
    row[16] = "1";
    row[20] = phase1_boundary_trace::Hex(payload);
    WriteBoundaryTraceRow(row);
}

void TrotExperiment::RecordBoundaryConsumption(
    const unitree_go::msg::dds_::LowState_ &state_snapshot,
    bool have_state,
    const unitree_go::msg::dds_::SportModeState_ &high_state_snapshot,
    bool have_high_state)
{
    if (!boundary_trace_enabled_ || !have_state ||
        !phase1_boundary_trace::InWindow(state_snapshot.tick()))
        return;
    const auto low_payload =
        phase1_boundary_trace::CanonicalLowState(state_snapshot);
    std::array<std::string, 22> row{};
    row[0] = "controller_consumption";
    row[1] = std::to_string(state_snapshot.tick());
    row[4] = boundary_pending_low_hash_;
    row[5] = boundary_pending_high_hash_;
    row[11] = std::to_string(boundary_pending_low_receipt_seq_);
    row[12] = std::to_string(boundary_pending_high_receipt_seq_);
    row[13] = std::to_string(boundary_pending_low_receipt_seq_);
    row[14] = std::to_string(boundary_pending_high_receipt_seq_);
    row[15] = "1";
    row[16] = have_high_state ? "1" : "0";
    row[17] = std::to_string(boundary_pending_control_seq_);
    row[19] = phase1_boundary_trace::Hex(low_payload);
    if (have_high_state)
    {
        const auto high_payload =
            phase1_boundary_trace::CanonicalHighState(high_state_snapshot);
        row[20] = phase1_boundary_trace::Hex(high_payload);
    }
    WriteBoundaryTraceRow(row);
}

void TrotExperiment::RecordBoundaryLowCmd(
    const unitree_go::msg::dds_::LowState_ &state_snapshot)
{
    if (!boundary_trace_enabled_ ||
        !phase1_boundary_trace::InWindow(state_snapshot.tick()))
        return;
    const auto state_payload =
        phase1_boundary_trace::CanonicalLowState(state_snapshot);
    const auto cmd_payload =
        phase1_boundary_trace::CanonicalLowCmd(low_cmd_);
    std::array<std::string, 22> row{};
    row[0] = "controller_lowcmd_prepublish";
    row[1] = std::to_string(state_snapshot.tick());
    row[4] = boundary_pending_low_hash_;
    row[5] = boundary_pending_high_hash_;
    row[11] = std::to_string(boundary_pending_low_receipt_seq_);
    row[12] = std::to_string(boundary_pending_high_receipt_seq_);
    row[13] = std::to_string(boundary_pending_low_receipt_seq_);
    row[14] = std::to_string(boundary_pending_high_receipt_seq_);
    row[15] = boundary_pending_have_state_ ? "1" : "0";
    row[16] = boundary_pending_have_high_state_ ? "1" : "0";
    row[17] = std::to_string(boundary_pending_control_seq_);
    row[18] = phase1_boundary_trace::Hash(cmd_payload);
    row[19] = phase1_boundary_trace::Hex(state_payload);
    row[21] = phase1_boundary_trace::Hex(cmd_payload);
    WriteBoundaryTraceRow(row);
}

void TrotExperiment::InitLowCmd()
{
    low_cmd_.head()[0] = 0xFE;
    low_cmd_.head()[1] = 0xEF;
    low_cmd_.level_flag() = 0xFF;
    low_cmd_.gpio() = 0;
    for (int i = 0; i < 20; ++i)
    {
        low_cmd_.motor_cmd()[i].mode() = 0x01;
        low_cmd_.motor_cmd()[i].q() = kPosStopF;
        low_cmd_.motor_cmd()[i].kp() = 0.0;
        low_cmd_.motor_cmd()[i].dq() = kVelStopF;
        low_cmd_.motor_cmd()[i].kd() = 0.0;
        low_cmd_.motor_cmd()[i].tau() = 0.0;
    }
}

// --- TrotExperiment::LowStateMessageHandler ---
void TrotExperiment::LowStateMessageHandler(const void *message)
{
    const unitree_go::msg::dds_::LowState_ *msg =
        static_cast<const unitree_go::msg::dds_::LowState_ *>(message);
    RecordBoundaryLowReceipt(*msg);
    // Order-108 verification-only tick gate: strictly-new-tick detection
    // and (once engaged) stale/reorder/gap fail-closed. No-op for the
    // wall-clock runner (adapter off -> gate never engaged).
    if (lockstep_ack_enabled_)
        lockstep_writer_gate_.OnLowState(msg->tick());
}

// --- TrotExperiment::HighStateMessageHandler ---
void TrotExperiment::HighStateMessageHandler(const void *message)
{
    RecordBoundaryHighReceipt(
        *(const unitree_go::msg::dds_::SportModeState_ *)message);
}

void TrotExperiment::EnvironmentHeightMapMessageHandler(const void *message)
{
    if (message == nullptr)
        return;
    std::lock_guard<std::mutex> lock(state_mutex_);
    const bool first_message = !have_environment_heightmap_;
    environment_heightmap_ =
        *static_cast<const unitree_go::msg::dds_::HeightMap_ *>(message);
    have_environment_heightmap_ = true;
    if (first_message)
    {
        std::cerr << "Environment map received: stamp="
                  << environment_heightmap_.stamp()
                  << " cells=" << environment_heightmap_.data().size()
                  << " frame=" << environment_heightmap_.frame_id() << "\n";
    }
}

// --- TrotExperiment::WaitForNaturalSettle ---
bool TrotExperiment::WaitForNaturalSettle(double timeout_s)
{
    const auto deadline = std::chrono::steady_clock::now() +
        std::chrono::duration<double>(timeout_s);
    auto stable_since = std::chrono::steady_clock::time_point{};

    while (std::chrono::steady_clock::now() < deadline)
    {
        bool stable = false;
        {
            std::lock_guard<std::mutex> lock(state_mutex_);
            if (have_low_state_)
            {
                double max_joint_speed = 0.0;
                double max_body_angular_speed = 0.0;
                for (int i = 0; i < kMotorCount; ++i)
                {
                    max_joint_speed = std::max(
                        max_joint_speed,
                        std::abs(static_cast<double>(
                            low_state_.motor_state()[i].dq())));
                }
                for (int axis = 0; axis < 3; ++axis)
                {
                    max_body_angular_speed = std::max(
                        max_body_angular_speed,
                        std::abs(static_cast<double>(
                            low_state_.imu_state().gyroscope()[axis])));
                }
                stable =
                    max_joint_speed <= 0.05 &&
                    max_body_angular_speed <= 0.05;
            }
        }
        const auto now = std::chrono::steady_clock::now();
        if (stable)
        {
            if (stable_since == std::chrono::steady_clock::time_point{})
                stable_since = now;
            if (now - stable_since >= std::chrono::duration<double>(0.5))
            {
                std::lock_guard<std::mutex> lock(state_mutex_);
                for (int i = 0; i < kMotorCount; ++i)
                    task_.start_joint_pos_[i] = low_state_.motor_state()[i].q();
                task_.have_start_joint_pos_ = true;
                std::cout << "Natural LowState settled\n";
                return true;
            }
        }
        else
        {
            stable_since = std::chrono::steady_clock::time_point{};
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    return false;
}

// --- TrotExperiment::CaptureWorldReference ---
bool TrotExperiment::CaptureWorldReference()
{
    std::lock_guard<std::mutex> lock(state_mutex_);
    if (!have_low_state_ || !have_high_state_)
    {
        std::cerr << "World reference unavailable; continue without world pose feedback\n";
        return false;
    }
    const WorldPose pose = ComputeWorldPose(low_state_, high_state_);
    world_reference_x_m_ = pose.base.x;
    world_reference_y_m_ = pose.base.y;
    world_reference_yaw_rad_ = pose.yaw_rad;
    have_world_reference_ = true;
    std::cout << "World reference captured: x=" << pose.base.x
              << " y=" << pose.base.y << " yaw=" << pose.yaw_rad << "\n";
    if (task_.goal_enabled_)
    {
        std::cout << "World A→B remaining="
                  << task_.RemainingXy(pose.base.x, pose.base.y)
                  << " m toward (" << task_.goal_x_ << ", "
                  << task_.goal_y_ << ")\n";
    }
    return true;
}

// --- TrotExperiment::PrepareLockstepHandoff ---
bool TrotExperiment::PrepareLockstepHandoff()
{
    if (!lockstep_ack_enabled_)
        return true;
    std::uint32_t handoff_tick = 0;
    {
        std::lock_guard<std::mutex> lock(state_mutex_);
        if (!have_low_state_)
        {
            std::cerr << "Lockstep handoff state unavailable\n";
            return false;
        }
        handoff_tick = low_state_.tick();
    }
    lockstep_handoff_state_tick_ = handoff_tick;
    lockstep_epoch_state_seq_ = handoff_tick;
    lockstep_epoch_valid_ = true;
    lockstep_handoff_prepared_ = true;
    lockstep_writer_gate_.PrepareForHandoff(handoff_tick);
    lockstep_motion_clock_.Engage(handoff_tick);
    std::cout << "Lockstep frozen capture tick=" << handoff_tick << "\n";
    std::cout << "Lockstep pre-motion handoff prepared: tick="
              << handoff_tick << "\n";
    return true;
}

void TrotExperiment::PublishLockstepReady(std::uint32_t state_tick)
{
    if (!lockstep_ack_enabled_)
        return;
#ifdef GO2_TROT_TESTING
    if (!lockstep_ready_publisher_)
    {
        if (suppress_lowcmd_publish_for_test_ &&
            state_tick == lockstep_handoff_state_tick_)
        {
            lockstep_ready_published_for_test_ = true;
            lockstep_ready_published_tick_for_test_ = state_tick;
        }
        return;
    }
#else
    if (!lockstep_ready_publisher_)
        return;
#endif
    unitree_go::msg::dds_::Error_ ready;
    ready.source(state_tick);
    ready.state(1);
    for (int i = 0; i < 3; ++i)
    {
        lockstep_ready_publisher_->Write(ready);
        if (i != 2)
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
#ifdef GO2_TROT_TESTING
    lockstep_ready_published_for_test_ = true;
    lockstep_ready_published_tick_for_test_ = state_tick;
#endif
    std::cout << "Lockstep READY published: tick=" << state_tick << "\n";
}


// --- TrotExperiment::Init ---
bool TrotExperiment::Init()
{
    csv_.open(csv_path_);
    if (!csv_)
    {
        std::cerr << "Failed to open CSV: " << csv_path_ << "\n";
        return false;
    }
    csv_ << std::fixed << std::setprecision(9);
    WriteCsvHeader();
    boundary_trace_enabled_ = phase1_boundary_trace::Enabled();
    if (boundary_trace_enabled_)
    {
        const std::string base = phase1_boundary_trace::BasePath();
        boundary_trace_csv_.open(base + ".controller.csv");
        if (!boundary_trace_csv_)
        {
            std::cerr << "Failed to open phase1 boundary controller trace: "
                      << base << ".controller.csv" << std::endl;
            boundary_trace_enabled_ = false;
        }
        else
        {
            boundary_trace_csv_
                << "record_type,tick,sequence,callback_seq,low_hash,"
                   "high_hash,high_source_generation,high_source_tick,"
                   "low_published,high_published,high_skipped,"
                   "low_receipt_seq,high_receipt_seq,consumed_low_receipt_seq,"
                   "consumed_high_receipt_seq,have_state,have_high_state,"
                   "control_seq,lowcmd_hash,low_payload_hex,high_payload_hex,"
                   "lowcmd_payload_hex\n";
        }
    }
    const char *publish_diag_env =
        std::getenv("TROT_LOCKSTEP_PUBLISH_DIAG");
    lockstep_publish_diag_enabled_ =
        publish_diag_env != nullptr && std::atof(publish_diag_env) > 0.5;
    if (lockstep_publish_diag_enabled_)
    {
        lockstep_publish_diag_csv_.open(csv_path_ + ".lockstep_publish.csv");
        if (!lockstep_publish_diag_csv_)
        {
            std::cerr << "Failed to open lockstep publish diagnostic CSV: "
                      << csv_path_ << ".lockstep_publish.csv\n";
            return false;
        }
        lockstep_publish_diag_csv_
            << "publish_index,steady_clock_ns,state_tick,lockstep_cmd_seq,"
               "lockstep_ack_enabled,lockstep_epoch_valid,gate_engaged,"
               "writer_branch,gait_started,stop_requested,sequence_finished,"
               "motion_stage,running_time_s,handoff_prepared,handoff_state_tick\n";
    }
    const char *closure_diag_env = std::getenv("TROT_DIAG_ID_CLOSURE");
    if (closure_diag_env != nullptr && std::atof(closure_diag_env) > 0.5)
    {
        closure_csv_.open(csv_path_ + ".id_closure.csv");
        if (!closure_csv_)
        {
            std::cerr << "Failed to open closure CSV: "
                      << csv_path_ << ".id_closure.csv\n";
            return false;
        }
        closure_csv_ << std::fixed << std::setprecision(9);
        WriteClosureCsvHeader();
    }
    InitLowCmd();
    const char *pd_pulse_env = std::getenv("TROT_PD_PULSE_AB");
    pd_pulse_enabled_ =
        pd_pulse_env != nullptr && std::atof(pd_pulse_env) > 0.5;
    const char *four_thigh_d90_env =
        std::getenv("TROT_FOUR_THIGH_D90_AB");
    four_thigh_d90_enabled_ =
        four_thigh_d90_env != nullptr && std::atof(four_thigh_d90_env) > 0.5;
    const char *bounded_stance_dq_env =
        std::getenv("TROT_BOUNDED_STANCE_DQ_D4_AB");
    bounded_stance_dq_enabled_ =
        bounded_stance_dq_env != nullptr &&
        std::atof(bounded_stance_dq_env) > 0.5;
    std::cout << "Bounded stance dq D4 AB enabled="
              << (bounded_stance_dq_enabled_ ? 1 : 0) << "\n";

    if (params_.wbc_full)
    {
#ifdef GO2_MODEL_PATH
        rigid_body_ = std::make_unique<go2_control::Go2RigidBody>();
        if (!rigid_body_->Load(GO2_MODEL_PATH))
        {
            std::cerr << "Failed to load Go2 MJCF for --wbc-full: "
                      << GO2_MODEL_PATH << "\n";
            return false;
        }
        std::cout << "WBC-FULL: 18-DoF MJCF model loaded\n";
#else
        std::cerr << "--wbc-full requires a controller-side MuJoCo model\n";
        return false;
#endif
    }

    std::cout << "Locomotion kernel: " << locomotion_kernel_->Name() << "\n";

    lowcmd_publisher_.reset(
        new ChannelPublisher<unitree_go::msg::dds_::LowCmd_>(GO2_TROT_TOPIC_LOWCMD));
    lowcmd_publisher_->InitChannel();
    if (const char *ack_env = std::getenv("TROT_LOCKSTEP_ACK");
        ack_env != nullptr && std::atof(ack_env) > 0.5)
    {
        lockstep_ack_publisher_.reset(
            new ChannelPublisher<unitree_go::msg::dds_::Error_>(
                GO2_TROT_TOPIC_LOCKSTEP_ACK));
        lockstep_ack_publisher_->InitChannel();
        lockstep_ready_publisher_.reset(
            new ChannelPublisher<unitree_go::msg::dds_::Error_>(
                GO2_TROT_TOPIC_LOCKSTEP_READY));
        lockstep_ready_publisher_->InitChannel();
        lockstep_ack_enabled_ = true;
        std::cout << "Lockstep ack adapter enabled on "
                  << GO2_TROT_TOPIC_LOCKSTEP_ACK << "\n";
        std::cout << "Lockstep READY publisher enabled on "
                  << GO2_TROT_TOPIC_LOCKSTEP_READY << "\n";
    }
    if (const char *timeout_env =
            std::getenv("TROT_LOCKSTEP_TICK_TIMEOUT_S");
        timeout_env != nullptr)
        lockstep_writer_gate_.SetTickWaitTimeoutS(
            std::atof(timeout_env));

    lowstate_subscriber_.reset(
        new ChannelSubscriber<unitree_go::msg::dds_::LowState_>(GO2_TROT_TOPIC_LOWSTATE));
    lowstate_subscriber_->InitChannel(
        std::bind(
            &TrotExperiment::LowStateMessageHandler,
            this,
            std::placeholders::_1),
        1);

    highstate_subscriber_.reset(
        new ChannelSubscriber<unitree_go::msg::dds_::SportModeState_>(
            GO2_TROT_TOPIC_HIGHSTATE));
    highstate_subscriber_->InitChannel(
        std::bind(
            &TrotExperiment::HighStateMessageHandler,
            this,
            std::placeholders::_1),
        1);

    if (params_.auto_environment)
    {
        environment_heightmap_subscriber_.reset(
            new ChannelSubscriber<unitree_go::msg::dds_::HeightMap_>(
                GO2_TROT_TOPIC_ENVIRONMENT_MAP));
        environment_heightmap_subscriber_->InitChannel(
            std::bind(
                &TrotExperiment::EnvironmentHeightMapMessageHandler,
                this,
                std::placeholders::_1),
            1);
        std::cout << "Automatic environment map: "
                  << GO2_TROT_TOPIC_ENVIRONMENT_MAP << "\n";
    }

    std::cout << "Waiting for natural settle...\n";
    if (!WaitForNaturalSettle(8.0))
    {
        std::cerr << "Natural settle timed out\n";
        return false;
    }
    CaptureWorldReference();
    if (!PrepareLockstepHandoff())
    {
        std::cerr << "Lockstep pre-motion handoff preparation failed\n";
        return false;
    }
    PublishLockstepReady(lockstep_handoff_state_tick_);

    writer_stop_.store(false);
    low_cmd_write_thread_ = std::thread([this]() {
        const auto interval = std::chrono::microseconds(
            static_cast<int64_t>(dt_ * 1000000.0));
        auto next = std::chrono::steady_clock::now();
        while (!writer_stop_.load() && !finished_.load())
        {
            // Order-108 verification-only tick gate: after the controller
            // handoff (TROT_LOCKSTEP_ACK on AND the first lockstep state
            // consumed post start-gait) the writer stops free-running on the
            // wall clock and consumes exactly ONE new physics tick per loop
            // iteration: one full LowCmdWrite/control update, one LowCmd
            // publish, one ack of the exact {state_seq, command_seq} pair,
            // then it waits for the next tick. Before the handoff -- and
            // whenever the adapter is off -- the original wall-clock
            // lifecycle below is unchanged.
            if (lockstep_ack_enabled_ && lockstep_handoff_prepared_)
            {
                EngageLockstepWriterIfNeeded();
                const lockstep_writer::WaitResult wait =
                    lockstep_writer_gate_.WaitForTick([this]() {
                        return writer_stop_.load() || finished_.load();
                    });
                if (wait == lockstep_writer::WaitResult::kAborted)
                    break;
                if (wait == lockstep_writer::WaitResult::kTimeout)
                {
                    // The gate already printed the
                    // TROT_LOCKSTEP_WRITER_FAIL_CLOSED diagnostic.
                    finished_.store(true);
                    break;
                }
                LowCmdWrite(true);
                lockstep_writer_gate_.RecordConsumed(
                    last_consumed_state_tick_);
            }
            else
            {
                LowCmdWrite(false);
                next += interval;
                std::this_thread::sleep_until(next);
                if (std::chrono::steady_clock::now() > next + interval * 4)
                    next = std::chrono::steady_clock::now();
            }
        }
    });
    return true;
}
void TrotExperiment::EngageLockstepWriterIfNeeded()
{
    if (lockstep_writer_gate_.Engaged())
        return;
    lockstep_writer_gate_.Engage(last_consumed_state_tick_);
    // Rebase the motion clock at the exact handoff tick so the first gated
    // update advances time once, not twice (or zero times) across transition.
    lockstep_motion_clock_.Engage(last_consumed_state_tick_);
}

// --- TrotExperiment::Shutdown ---
void TrotExperiment::Shutdown()
{
    writer_stop_.store(true);
    if (low_cmd_write_thread_.joinable())
        low_cmd_write_thread_.join();
    csv_.close();
    closure_csv_.close();
    lockstep_publish_diag_csv_.close();
}

// --- TrotExperiment::RequestStop ---
void TrotExperiment::RequestStop()
{
    if (!external_stop_requested_.exchange(true))
    {
        task_.task_completion_requested_ = false;
        std::cout << "Trot external stop requested; returning to stand\n";
    }
}

// --- TrotExperiment::StopFileRequested ---
bool TrotExperiment::StopFileRequested() const
{
    if (stop_file_path_.empty())
        return false;
    std::ifstream stop_file(stop_file_path_);
    return stop_file.good();
}
