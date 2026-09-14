#pragma once

#include <mujoco/mujoco.h>

#include <unitree/robot/channel/channel_publisher.hpp>
#include <unitree/robot/channel/channel_subscriber.hpp>
#include <unitree/dds_wrapper/robots/go2/go2.h>
#include <unitree/dds_wrapper/robots/g1/g1.h>
#include <unitree/idl/go2/Error_.hpp>
#include <unitree/idl/go2/HeightMap_.hpp>
#include <unitree/idl/hg/BmsState_.hpp>
#include <unitree/idl/hg/IMUState_.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>
#include <limits>
#include <mutex>
#include <type_traits>

#include "param.h"
#include "physics_joystick.h"
#include "lockstep.h"


#define MOTOR_SENSOR_NUM 3

namespace lockstep { class Coordinator; }
extern lockstep::Coordinator *g_lockstep;

namespace go2_bridge
{
constexpr std::size_t kAtomicMotorCount = 12;


struct AtomicBridgeRecord
{
    std::uint64_t bridge_ctrl_seq = 0;
    std::uint32_t motor_count = 0;
    double sim_time_s = 0.0;
    std::array<double, kAtomicMotorCount> q{};
    std::array<double, kAtomicMotorCount> dq{};
    std::array<double, kAtomicMotorCount> kp{};
    std::array<double, kAtomicMotorCount> kd{};
    std::array<double, kAtomicMotorCount> tau_ff{};
    std::array<double, kAtomicMotorCount> sensor_q{};
    std::array<double, kAtomicMotorCount> sensor_dq{};
    std::array<double, kAtomicMotorCount> ctrl{};
};

class AtomicBridgeCapture
{
public:
    AtomicBridgeCapture()
        : enabled_(ParseEnabled(std::getenv("TROT_BRIDGE_ATOMIC_RECORD")))
    {
    }

    bool enabled() const
    {
        return enabled_;
    }

    const AtomicBridgeRecord &record() const
    {
        return record_;
    }

    void Publish(AtomicBridgeRecord record)
    {
        record.bridge_ctrl_seq = ++next_seq_;
        record_ = record;
    }

private:
    static bool ParseEnabled(const char *value)
    {
        return value != nullptr &&
            (std::string(value) == "1" || std::string(value) == "true");
    }

    const bool enabled_ = false;
    std::uint64_t next_seq_ = 0;
    AtomicBridgeRecord record_;
};

inline AtomicBridgeCapture atomic_bridge_capture;
}  // namespace go2_bridge
class UnitreeSDK2BridgeBase
{
public:
    UnitreeSDK2BridgeBase(
        mjModel *model,
        mjData *data,
        std::recursive_mutex *sim_mutex)
    : mj_model_(model), mj_data_(data), sim_mutex_(sim_mutex)
    {
        _check_sensor();
        if(param::config.print_scene_information == 1) {
            printSceneInformation();
        }
        if(param::config.use_joystick == 1) {
            if(param::config.joystick_type == "xbox") {
                joystick = std::make_shared<XBoxJoystick>(param::config.joystick_device, param::config.joystick_bits);
            } else if(param::config.joystick_type == "switch") {
                joystick  = std::make_shared<SwitchJoystick>(param::config.joystick_device, param::config.joystick_bits);
            } else {
                std::cerr << "Unsupported joystick type: " << param::config.joystick_type << std::endl;
                exit(EXIT_FAILURE);
            }
        }

    }

    virtual void start() {}

    void printSceneInformation()
    {
        auto printObjects = [this](const char* title, int count, int type, auto getIndex) {
            std::cout << "<<------------- " << title << " ------------->> " << std::endl;
            for (int i = 0; i < count; i++) {
                const char* name = mj_id2name(mj_model_, type, i);
                if (name) {
                    std::cout << title << "_index: " << getIndex(i) << ", " << "name: " << name;
                    if (type == mjOBJ_SENSOR) {
                        std::cout << ", dim: " << mj_model_->sensor_dim[i];
                    }
                    std::cout << std::endl;
                }
            }
            std::cout << std::endl;
        };
    
        printObjects("Link", mj_model_->nbody, mjOBJ_BODY, [](int i) { return i; });
        printObjects("Joint", mj_model_->njnt, mjOBJ_JOINT, [](int i) { return i; });
        printObjects("Actuator", mj_model_->nu, mjOBJ_ACTUATOR, [](int i) { return i; });
    
        int sensorIndex = 0;
        printObjects("Sensor", mj_model_->nsensor, mjOBJ_SENSOR, [&](int i) {
            int currentIndex = sensorIndex;
            sensorIndex += mj_model_->sensor_dim[i];
            return currentIndex;
        });
    }

protected:
    int num_motor_ = 0;
    int dim_motor_sensor_ = 0;

    mjData *mj_data_;
    mjModel *mj_model_;
    std::recursive_mutex *sim_mutex_ = nullptr;

    std::unique_lock<std::recursive_mutex> LockSimulation()
    {
        if (sim_mutex_ == nullptr)
        {
            return {};
        }
        return std::unique_lock<std::recursive_mutex>(*sim_mutex_);
    }

    // Sensor data indices
    int imu_quat_adr_ = -1;
    int imu_gyro_adr_ = -1;
    int imu_acc_adr_ = -1;
    int frame_pos_adr_ = -1;
    int frame_vel_adr_ = -1;
    std::array<int, 4> foot_force_adr_ = {-1, -1, -1, -1};

    int secondary_imu_quat_adr_ = -1;
    int secondary_imu_gyro_adr_ = -1;
    int secondary_imu_acc_adr_ = -1;

    std::shared_ptr<unitree::common::UnitreeJoystick> joystick = nullptr;

    void _check_sensor()
    {
        num_motor_ = mj_model_->nu;
        dim_motor_sensor_ = MOTOR_SENSOR_NUM * num_motor_;
    
        // Find sensor addresses by name
        int sensor_id = -1;
        
        // IMU quaternion
        sensor_id = mj_name2id(mj_model_, mjOBJ_SENSOR, "imu_quat");
        if (sensor_id >= 0) {
            imu_quat_adr_ = mj_model_->sensor_adr[sensor_id];
        }
        
        // IMU gyroscope
        sensor_id = mj_name2id(mj_model_, mjOBJ_SENSOR, "imu_gyro");
        if (sensor_id >= 0) {
            imu_gyro_adr_ = mj_model_->sensor_adr[sensor_id];
        }
        
        // IMU accelerometer
        sensor_id = mj_name2id(mj_model_, mjOBJ_SENSOR, "imu_acc");
        if (sensor_id >= 0) {
            imu_acc_adr_ = mj_model_->sensor_adr[sensor_id];
        }
        
        // Frame position
        sensor_id = mj_name2id(mj_model_, mjOBJ_SENSOR, "frame_pos");
        if (sensor_id >= 0) {
            frame_pos_adr_ = mj_model_->sensor_adr[sensor_id];
        }
        
        // Frame velocity
        sensor_id = mj_name2id(mj_model_, mjOBJ_SENSOR, "frame_vel");
        if (sensor_id >= 0) {
            frame_vel_adr_ = mj_model_->sensor_adr[sensor_id];
        }

        const std::array<const char *, 4> foot_force_sensor_names = {
            "FR_foot_force", "FL_foot_force", "RR_foot_force", "RL_foot_force"};
        for (std::size_t i = 0; i < foot_force_sensor_names.size(); ++i) {
            sensor_id = mj_name2id(
                mj_model_, mjOBJ_SENSOR, foot_force_sensor_names[i]);
            if (sensor_id >= 0) {
                foot_force_adr_[i] = mj_model_->sensor_adr[sensor_id];
            }
        }

        // Secondary IMU quaternion
        sensor_id = mj_name2id(mj_model_, mjOBJ_SENSOR, "secondary_imu_quat");
        if (sensor_id >= 0) {
            secondary_imu_quat_adr_ = mj_model_->sensor_adr[sensor_id];
        }

        // Secondary IMU gyroscope
        sensor_id = mj_name2id(mj_model_, mjOBJ_SENSOR, "secondary_imu_gyro");
        if (sensor_id >= 0) {
            secondary_imu_gyro_adr_ = mj_model_->sensor_adr[sensor_id];
        }

        // Secondary IMU accelerometer
        sensor_id = mj_name2id(mj_model_, mjOBJ_SENSOR, "secondary_imu_acc");
        if (sensor_id >= 0) {
            secondary_imu_acc_adr_ = mj_model_->sensor_adr[sensor_id];
        }
    }


};
// LowCmd subscription that counts every DDS arrival so the lockstep
// exchange rule can wait for a full controller write period. Message state
// handling is identical to SubscriptionBase's default handler; the
// wall-clock path keeps the plain LowCmd_t and is byte-identical.
template <typename MsgType>
class CountingLowCmd : public unitree::robot::SubscriptionBase<MsgType>
{
public:
    CountingLowCmd(const std::string &topic, lockstep::Coordinator *coord)
        : unitree::robot::SubscriptionBase<MsgType>(
              topic, [this, coord](const void *msg) {
                  if (coord != nullptr) coord->OnCommandArrived();
                  std::lock_guard<std::mutex> lock(this->mutex_);
                  this->msg_ = *(const MsgType *)msg;
              })
    {
    }
};

// Ack metadata subscriber for the exact {state_seq, command_seq} pair.
class LockstepAckSubscriber
    : public unitree::robot::SubscriptionBase<unitree_go::msg::dds_::Error_>
{
public:
    explicit LockstepAckSubscriber(const std::string &topic,
                                   lockstep::Coordinator *coord)
        : unitree::robot::SubscriptionBase<unitree_go::msg::dds_::Error_>(
              topic, [coord](const void *msg) {
                  if (coord == nullptr) return;
                  const auto *m = static_cast<
                      const unitree_go::msg::dds_::Error_ *>(msg);
                  coord->OnAckReceived(m->source(), m->state());
              })
    {
    }
};

template <typename LowCmd_t, typename LowState_t>
class RobotBridge : public UnitreeSDK2BridgeBase
{
using HighState_t = unitree::robot::go2::publisher::SportModeState;
using WirelessController_t = unitree::robot::go2::publisher::WirelessController;

public:
    RobotBridge(
        mjModel *model,
        mjData *data,
        std::recursive_mutex *sim_mutex)
        : UnitreeSDK2BridgeBase(model, data, sim_mutex)
    {
        if (param::config.lockstep)
        {
            lowcmd = std::make_shared<CountingLowCmd<
                typename LowCmd_t::MsgType>>("rt/lowcmd", ::g_lockstep);
            lockstep_ack_subscriber_ =
                std::make_shared<LockstepAckSubscriber>(
                    "rt/lockstep/ack", ::g_lockstep);
        }
        else
        {
            lowcmd = std::make_shared<LowCmd_t>("rt/lowcmd");
        }
        lowstate = std::make_unique<LowState_t>();
        lowstate->joystick = joystick;
        highstate = std::make_unique<HighState_t>();
        environment_heightmap = unitree::robot::ChannelFactory::Instance()
            ->CreateSendChannel<unitree_go::msg::dds_::HeightMap_>(
                "rt/go2/environment_heightmap");
        wireless_controller = std::make_unique<WirelessController_t>();
        wireless_controller->joystick = joystick;
    }

    void start()
    {
        thread_ = std::make_shared<unitree::common::RecurrentThread>(
            "unitree_bridge", UT_CPU_ID_NONE, 1000, [this]() { this->run(); });
    }

    void PublishEnvironmentHeightMap()
    {
        constexpr float kResolution = 0.10f;
        constexpr uint32_t kWidth = 16;
        constexpr uint32_t kHeight = 16;
        constexpr float kOriginX = -0.20f;
        constexpr float kOriginY = -0.80f;
        const double sim_time = mj_data_->time;
        if (!environment_heightmap ||
            sim_time - last_environment_map_publish_s_ < 0.020)
            return;
        const int base_body_id = mj_name2id(
            mj_model_, mjOBJ_BODY, "base_link");
        if (base_body_id < 0)
            return;
        unitree_go::msg::dds_::HeightMap_ map;
        map.stamp(sim_time);
        map.frame_id("base_link");
        map.resolution(kResolution);
        map.width(kWidth);
        map.height(kHeight);
        map.origin() = {kOriginX, kOriginY};
        map.data().assign(
            static_cast<std::size_t>(kWidth) * kHeight, 0.0f);
        const mjtNum *base_pos = mj_data_->xpos + 3 * base_body_id;
        const mjtNum *base_mat = mj_data_->xmat + 9 * base_body_id;
        for (int geom_id = 0; geom_id < mj_model_->ngeom; ++geom_id)
        {
            if (mj_model_->geom_bodyid[geom_id] != 0 ||
                mj_model_->geom_type[geom_id] == mjGEOM_PLANE ||
                (mj_model_->geom_contype[geom_id] == 0 &&
                 mj_model_->geom_conaffinity[geom_id] == 0))
                continue;
            double footprint_radius = 0.0;
            double half_height = 0.0;
            const int type = mj_model_->geom_type[geom_id];
            const mjtNum *size = mj_model_->geom_size + 3 * geom_id;
            if (type == mjGEOM_BOX)
            {
                footprint_radius = std::hypot(size[0], size[1]);
                half_height = size[2];
            }
            else if (type == mjGEOM_CYLINDER)
            {
                footprint_radius = size[0];
                half_height = size[1];
            }
            else if (type == mjGEOM_CAPSULE)
            {
                footprint_radius = size[0];
                half_height = size[1] + size[0];
            }
            else if (type == mjGEOM_SPHERE)
            {
                footprint_radius = size[0];
                half_height = size[0];
            }
            else
            {
                footprint_radius = std::max(size[0], size[1]);
                half_height = std::max(size[0], size[2]);
            }
            if (!(footprint_radius > 0.0) || !(half_height > 0.0))
                continue;
            const mjtNum *geom_pos = mj_data_->geom_xpos + 3 * geom_id;
            const mjtNum *geom_delta = geom_pos;
            mjtNum world_delta[3] = {
                geom_delta[0] - base_pos[0],
                geom_delta[1] - base_pos[1],
                geom_delta[2] - base_pos[2]};
            mjtNum local[3] = {0.0, 0.0, 0.0};
            mju_mulMatTVec(local, base_mat, world_delta, 3, 3);
            const double top = geom_pos[2] + half_height;
            for (uint32_t iy = 0; iy < kHeight; ++iy)
            {
                const double y = kOriginY +
                    (static_cast<double>(iy) + 0.5) * kResolution;
                for (uint32_t ix = 0; ix < kWidth; ++ix)
                {
                    const double x = kOriginX +
                        (static_cast<double>(ix) + 0.5) * kResolution;
                    if (std::hypot(x - local[0], y - local[1]) >
                        footprint_radius + 0.5 * kResolution)
                        continue;
                    const std::size_t index =
                        static_cast<std::size_t>(iy) * kWidth + ix;
                    map.data()[index] = std::max(
                        map.data()[index], static_cast<float>(top));
                }
            }
        }
        (void)environment_heightmap->Write(map, 0);
        last_environment_map_publish_s_ = sim_time;
    }

    virtual void run()
    {
        if (param::config.lockstep && ::g_lockstep != nullptr)
        {
            RunLockstep();
            return;
        }
        RunWallClock();
    }

    void RunWallClock()
    {
        auto sim_lock = LockSimulation();
        if(!mj_data_) return;
        if(lowstate->joystick) { lowstate->joystick->update(); }
        // lowcmd
        {
            std::lock_guard<std::mutex> lock(lowcmd->mutex_);
            const bool capture_atomic =
                go2_bridge::atomic_bridge_capture.enabled();
            go2_bridge::AtomicBridgeRecord atomic_record;
            for(int i(0); i<num_motor_; i++) {
                auto & m = lowcmd->msg_.motor_cmd()[i];
                const mjtNum sensor_q = mj_data_->sensordata[i];
                const mjtNum sensor_dq =
                    mj_data_->sensordata[i + num_motor_];
                const mjtNum ctrl = m.tau() +
                                    m.kp() * (m.q() - mj_data_->sensordata[i]) +
                                    m.kd() * (m.dq() -
                                               mj_data_->sensordata[i + num_motor_]);
                mj_data_->ctrl[i] = ctrl;
                if (capture_atomic &&
                    i < static_cast<int>(go2_bridge::kAtomicMotorCount)) {
                    atomic_record.q[static_cast<std::size_t>(i)] = m.q();
                    atomic_record.dq[static_cast<std::size_t>(i)] = m.dq();
                    atomic_record.kp[static_cast<std::size_t>(i)] = m.kp();
                    atomic_record.kd[static_cast<std::size_t>(i)] = m.kd();
                    atomic_record.tau_ff[static_cast<std::size_t>(i)] = m.tau();
                    atomic_record.sensor_q[static_cast<std::size_t>(i)] = sensor_q;
                    atomic_record.sensor_dq[static_cast<std::size_t>(i)] = sensor_dq;
                    atomic_record.ctrl[static_cast<std::size_t>(i)] =
                        mj_data_->ctrl[i];
                }
            }
            if (capture_atomic) {
                atomic_record.motor_count =
                    static_cast<std::uint32_t>(num_motor_);
                atomic_record.sim_time_s = mj_data_->time;
                go2_bridge::atomic_bridge_capture.Publish(atomic_record);
            }
        }

        PublishEnvironmentHeightMap();

        // lowstate
        if(lowstate->trylock()) {
            for(int i(0); i<num_motor_; i++) {
                lowstate->msg_.motor_state()[i].q() = mj_data_->sensordata[i];
                lowstate->msg_.motor_state()[i].dq() = mj_data_->sensordata[i + num_motor_];
                lowstate->msg_.motor_state()[i].tau_est() = mj_data_->sensordata[i + 2 * num_motor_];
            }
            
            if(imu_quat_adr_ >= 0) {
                lowstate->msg_.imu_state().quaternion()[0] = mj_data_->sensordata[imu_quat_adr_ + 0];
                lowstate->msg_.imu_state().quaternion()[1] = mj_data_->sensordata[imu_quat_adr_ + 1];
                lowstate->msg_.imu_state().quaternion()[2] = mj_data_->sensordata[imu_quat_adr_ + 2];
                lowstate->msg_.imu_state().quaternion()[3] = mj_data_->sensordata[imu_quat_adr_ + 3];

                double w = lowstate->msg_.imu_state().quaternion()[0];
                double x = lowstate->msg_.imu_state().quaternion()[1];
                double y = lowstate->msg_.imu_state().quaternion()[2];
                double z = lowstate->msg_.imu_state().quaternion()[3];

                lowstate->msg_.imu_state().rpy()[0] = atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y));
                lowstate->msg_.imu_state().rpy()[1] = asin(2 * (w * y - z * x));
                lowstate->msg_.imu_state().rpy()[2] = atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z));
            }
            
            if(imu_gyro_adr_ >= 0) {
                lowstate->msg_.imu_state().gyroscope()[0] = mj_data_->sensordata[imu_gyro_adr_ + 0];
                lowstate->msg_.imu_state().gyroscope()[1] = mj_data_->sensordata[imu_gyro_adr_ + 1];
                lowstate->msg_.imu_state().gyroscope()[2] = mj_data_->sensordata[imu_gyro_adr_ + 2];
            }

            if(imu_acc_adr_ >= 0) {
                lowstate->msg_.imu_state().accelerometer()[0] = mj_data_->sensordata[imu_acc_adr_ + 0];
                lowstate->msg_.imu_state().accelerometer()[1] = mj_data_->sensordata[imu_acc_adr_ + 1];
                lowstate->msg_.imu_state().accelerometer()[2] = mj_data_->sensordata[imu_acc_adr_ + 2];
            }

            if constexpr (std::is_same_v<
                              std::decay_t<decltype(lowstate->msg_)>,
                              unitree_go::msg::dds_::LowState_>) {
                for(std::size_t i = 0; i < foot_force_adr_.size(); ++i) {
                    if(foot_force_adr_[i] >= 0) {
                        const double force = std::clamp(
                            mj_data_->sensordata[foot_force_adr_[i]],
                            0.0,
                            static_cast<double>(std::numeric_limits<int16_t>::max()));
                        const int16_t force_value =
                            static_cast<int16_t>(std::lround(force));
                        lowstate->msg_.foot_force()[i] = force_value;
                        lowstate->msg_.foot_force_est()[i] = force_value;
                    }
                }
            }
            
            // [动力学槽位] motor_state[12..17] 的 7 个 float 字段:
            // slot 0-35 = 基座质量矩阵 6x6(qM 展开), slot 36-41 = base qfrc_bias(6)
            if constexpr (std::is_same_v<
                              std::decay_t<decltype(lowstate->msg_)>,
                              unitree_go::msg::dds_::LowState_>) {
                static thread_local std::vector<mjtNum> full_mass(
                    static_cast<std::size_t>(mj_model_->nv) *
                    static_cast<std::size_t>(mj_model_->nv), 0.0);
                mj_fullM(mj_model_, full_mass.data(), mj_data_->qM);
                for (int slot = 0; slot < 42; ++slot) {
                    const int motor = 12 + slot / 7;
                    const int field = slot % 7;
                    double value = 0.0;
                    if (slot < 36) {
                        const int r = slot / 6;
                        const int c = slot % 6;
                        value = full_mass[static_cast<std::size_t>(
                            r * mj_model_->nv + c)];
                    } else {
                        value = mj_data_->qfrc_bias[slot - 36];
                    }
                    auto &ms = lowstate->msg_.motor_state()[motor];
                    switch (field) {
                        case 0: ms.q() = static_cast<float>(value); break;
                        case 1: ms.dq() = static_cast<float>(value); break;
                        case 2: ms.ddq() = static_cast<float>(value); break;
                        case 3: ms.tau_est() = static_cast<float>(value); break;
                        case 4: ms.q_raw() = static_cast<float>(value); break;
                        case 5: ms.dq_raw() = static_cast<float>(value); break;
                        case 6: ms.ddq_raw() = static_cast<float>(value); break;
                    }
                }
            }

            lowstate->msg_.tick() = std::round(mj_data_->time / 1e-3);
            lowstate->unlockAndPublish();
        }
        // highstate
        if(highstate->trylock()) {
            if(frame_pos_adr_ >= 0) {
                highstate->msg_.position()[0] = mj_data_->sensordata[frame_pos_adr_ + 0];
                highstate->msg_.position()[1] = mj_data_->sensordata[frame_pos_adr_ + 1];
                highstate->msg_.position()[2] = mj_data_->sensordata[frame_pos_adr_ + 2];
            }
            if(frame_vel_adr_ >= 0) {
                highstate->msg_.velocity()[0] = mj_data_->sensordata[frame_vel_adr_ + 0];
                highstate->msg_.velocity()[1] = mj_data_->sensordata[frame_vel_adr_ + 1];
                highstate->msg_.velocity()[2] = mj_data_->sensordata[frame_vel_adr_ + 2];
            }
            highstate->unlockAndPublish();
        }
        // wireless_controller
        if(wireless_controller->joystick) {
            wireless_controller->unlockAndPublish();
        }
    }

    std::unique_ptr<HighState_t> highstate;
    void RunLockstep()
    {
        if (!::g_lockstep->BarrierComplete())
        {
            RunWallClock();
            ::g_lockstep->OnStartupPublish(CurrentTickMs());
            return;
        }
        auto sim_lock = LockSimulation();
        if (!mj_data_) return;
        if (::g_lockstep->FailedClosed()) return;
        const std::uint64_t sim_tick_ms = CurrentTickMs();
        const lockstep::PublishOutcome outcome =
            ::g_lockstep->OnPublish(sim_tick_ms);
        PublishStateSnapshot(/*blocking_lowstate=*/true);
        if (outcome == lockstep::PublishOutcome::kStepGranted)
        {
            ApplyLatestCommand();
            ::g_lockstep->NotifyCommandApplied();
        }
    }

    std::uint64_t CurrentTickMs() const
    {
        return static_cast<std::uint64_t>(
            std::llround(mj_data_->time * 1000.0));
    }

    void ApplyLatestCommand()
    {
        auto sim_lock = LockSimulation();
        if (!mj_data_) return;
        std::lock_guard<std::mutex> lock(lowcmd->mutex_);
        const bool capture_atomic =
            go2_bridge::atomic_bridge_capture.enabled();
        go2_bridge::AtomicBridgeRecord atomic_record;
        for (int i = 0; i < num_motor_; i++)
        {
            auto &motor = lowcmd->msg_.motor_cmd()[i];
            const mjtNum sensor_q = mj_data_->sensordata[i];
            const mjtNum sensor_dq =
                mj_data_->sensordata[i + num_motor_];
            mj_data_->ctrl[i] = motor.tau() +
                motor.kp() * (motor.q() - sensor_q) +
                motor.kd() * (motor.dq() - sensor_dq);
            if (capture_atomic &&
                i < static_cast<int>(go2_bridge::kAtomicMotorCount))
            {
                atomic_record.q[static_cast<std::size_t>(i)] = motor.q();
                atomic_record.dq[static_cast<std::size_t>(i)] = motor.dq();
                atomic_record.kp[static_cast<std::size_t>(i)] = motor.kp();
                atomic_record.kd[static_cast<std::size_t>(i)] = motor.kd();
                atomic_record.tau_ff[static_cast<std::size_t>(i)] =
                    motor.tau();
                atomic_record.sensor_q[static_cast<std::size_t>(i)] = sensor_q;
                atomic_record.sensor_dq[static_cast<std::size_t>(i)] = sensor_dq;
                atomic_record.ctrl[static_cast<std::size_t>(i)] =
                    mj_data_->ctrl[i];
            }
        }
        if (capture_atomic)
        {
            atomic_record.motor_count =
                static_cast<std::uint32_t>(num_motor_);
            atomic_record.sim_time_s = mj_data_->time;
            go2_bridge::atomic_bridge_capture.Publish(atomic_record);
        }
    }

    void PublishStateSnapshot(bool blocking_lowstate)
    {
        auto sim_lock = LockSimulation();
        if (!mj_data_) return;
        PublishEnvironmentHeightMap();
        const bool lowstate_locked =
            blocking_lowstate ? (lowstate->lock(), true) : lowstate->trylock();
        if (lowstate_locked)
        {
            for (int i = 0; i < num_motor_; i++)
            {
                lowstate->msg_.motor_state()[i].q() =
                    mj_data_->sensordata[i];
                lowstate->msg_.motor_state()[i].dq() =
                    mj_data_->sensordata[i + num_motor_];
                lowstate->msg_.motor_state()[i].tau_est() =
                    mj_data_->sensordata[i + 2 * num_motor_];
            }
            if (imu_quat_adr_ >= 0)
            {
                lowstate->msg_.imu_state().quaternion()[0] =
                    mj_data_->sensordata[imu_quat_adr_ + 0];
                lowstate->msg_.imu_state().quaternion()[1] =
                    mj_data_->sensordata[imu_quat_adr_ + 1];
                lowstate->msg_.imu_state().quaternion()[2] =
                    mj_data_->sensordata[imu_quat_adr_ + 2];
                lowstate->msg_.imu_state().quaternion()[3] =
                    mj_data_->sensordata[imu_quat_adr_ + 3];
                const double w = lowstate->msg_.imu_state().quaternion()[0];
                const double x = lowstate->msg_.imu_state().quaternion()[1];
                const double y = lowstate->msg_.imu_state().quaternion()[2];
                const double z = lowstate->msg_.imu_state().quaternion()[3];
                lowstate->msg_.imu_state().rpy()[0] =
                    atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y));
                lowstate->msg_.imu_state().rpy()[1] =
                    asin(2 * (w * y - z * x));
                lowstate->msg_.imu_state().rpy()[2] =
                    atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z));
            }
            if (imu_gyro_adr_ >= 0)
            {
                lowstate->msg_.imu_state().gyroscope()[0] =
                    mj_data_->sensordata[imu_gyro_adr_ + 0];
                lowstate->msg_.imu_state().gyroscope()[1] =
                    mj_data_->sensordata[imu_gyro_adr_ + 1];
                lowstate->msg_.imu_state().gyroscope()[2] =
                    mj_data_->sensordata[imu_gyro_adr_ + 2];
            }
            if (imu_acc_adr_ >= 0)
            {
                lowstate->msg_.imu_state().accelerometer()[0] =
                    mj_data_->sensordata[imu_acc_adr_ + 0];
                lowstate->msg_.imu_state().accelerometer()[1] =
                    mj_data_->sensordata[imu_acc_adr_ + 1];
                lowstate->msg_.imu_state().accelerometer()[2] =
                    mj_data_->sensordata[imu_acc_adr_ + 2];
            }
            if constexpr (std::is_same_v<
                              std::decay_t<decltype(lowstate->msg_)>,
                              unitree_go::msg::dds_::LowState_>)
            {
                for (std::size_t i = 0; i < foot_force_adr_.size(); ++i)
                {
                    if (foot_force_adr_[i] >= 0)
                    {
                        const double force = std::clamp(
                            mj_data_->sensordata[foot_force_adr_[i]],
                            0.0,
                            static_cast<double>(
                                std::numeric_limits<int16_t>::max()));
                        const int16_t force_value =
                            static_cast<int16_t>(std::lround(force));
                        lowstate->msg_.foot_force()[i] = force_value;
                        lowstate->msg_.foot_force_est()[i] = force_value;
                    }
                }
                static thread_local std::vector<mjtNum> full_mass(
                    static_cast<std::size_t>(mj_model_->nv) *
                    static_cast<std::size_t>(mj_model_->nv), 0.0);
                mj_fullM(mj_model_, full_mass.data(), mj_data_->qM);
                for (int slot = 0; slot < 42; ++slot)
                {
                    const int motor = 12 + slot / 7;
                    const int field = slot % 7;
                    double value = 0.0;
                    if (slot < 36)
                    {
                        const int r = slot / 6;
                        const int c = slot % 6;
                        value = full_mass[static_cast<std::size_t>(
                            r * mj_model_->nv + c)];
                    }
                    else
                    {
                        value = mj_data_->qfrc_bias[slot - 36];
                    }
                    auto &ms = lowstate->msg_.motor_state()[motor];
                    switch (field)
                    {
                        case 0: ms.q() = static_cast<float>(value); break;
                        case 1: ms.dq() = static_cast<float>(value); break;
                        case 2: ms.ddq() = static_cast<float>(value); break;
                        case 3: ms.tau_est() = static_cast<float>(value); break;
                        case 4: ms.q_raw() = static_cast<float>(value); break;
                        case 5: ms.dq_raw() = static_cast<float>(value); break;
                        case 6: ms.ddq_raw() = static_cast<float>(value); break;
                    }
                }
            }
            lowstate->msg_.tick() =
                static_cast<std::uint32_t>(
                    std::llround(mj_data_->time / 1e-3));
            lowstate->unlockAndPublish();
        }
        if (highstate->trylock())
        {
            if (frame_pos_adr_ >= 0)
            {
                highstate->msg_.position()[0] =
                    mj_data_->sensordata[frame_pos_adr_ + 0];
                highstate->msg_.position()[1] =
                    mj_data_->sensordata[frame_pos_adr_ + 1];
                highstate->msg_.position()[2] =
                    mj_data_->sensordata[frame_pos_adr_ + 2];
            }
            if (frame_vel_adr_ >= 0)
            {
                highstate->msg_.velocity()[0] =
                    mj_data_->sensordata[frame_vel_adr_ + 0];
                highstate->msg_.velocity()[1] =
                    mj_data_->sensordata[frame_vel_adr_ + 1];
                highstate->msg_.velocity()[2] =
                    mj_data_->sensordata[frame_vel_adr_ + 2];
            }
            highstate->unlockAndPublish();
        }
        if (wireless_controller->joystick)
            wireless_controller->unlockAndPublish();
    }
    unitree::robot::ChannelPtr<unitree_go::msg::dds_::HeightMap_> environment_heightmap;
    std::unique_ptr<WirelessController_t> wireless_controller;
    std::shared_ptr<unitree::robot::SubscriptionBase<typename LowCmd_t::MsgType>> lowcmd;
    std::unique_ptr<LowState_t> lowstate;
    std::shared_ptr<LockstepAckSubscriber> lockstep_ack_subscriber_;
    
private:
    double last_environment_map_publish_s_ = -1.0e9;
    unitree::common::RecurrentThreadPtr thread_;
};

using Go2Bridge = RobotBridge<unitree::robot::go2::subscription::LowCmd, unitree::robot::go2::publisher::LowState>;

class G1Bridge : public RobotBridge<unitree::robot::g1::subscription::LowCmd, unitree::robot::g1::publisher::LowState>
{
public:
    G1Bridge(
        mjModel *model,
        mjData *data,
        std::recursive_mutex *sim_mutex)
        : RobotBridge(model, data, sim_mutex)
    {
        if (param::config.robot.find("g1") != std::string::npos) {
            auto* g1_lowstate = dynamic_cast<unitree::robot::g1::publisher::LowState*>(lowstate.get());
            if (g1_lowstate) {
                auto scene = param::config.robot_scene.filename().string();
                g1_lowstate->msg_.mode_machine() = scene.find("23") != std::string::npos ? 4 : 5;
            }
        }

        bmsstate = std::make_unique<BmsState_t>("rt/lf/bmsstate");
        bmsstate->msg_.soc() = 100;

        secondary_imustate = std::make_unique<IMUState_t>("rt/secondary_imu");
    }

    void run() override
    {
        RobotBridge::run();
        auto sim_lock = LockSimulation();

        // secondary IMU state
        if (secondary_imustate->trylock()) {
            if(secondary_imu_quat_adr_ >= 0) {
                secondary_imustate->msg_.quaternion()[0] = mj_data_->sensordata[secondary_imu_quat_adr_ + 0];
                secondary_imustate->msg_.quaternion()[1] = mj_data_->sensordata[secondary_imu_quat_adr_ + 1];
                secondary_imustate->msg_.quaternion()[2] = mj_data_->sensordata[secondary_imu_quat_adr_ + 2];
                secondary_imustate->msg_.quaternion()[3] = mj_data_->sensordata[secondary_imu_quat_adr_ + 3];

                double w = secondary_imustate->msg_.quaternion()[0];
                double x = secondary_imustate->msg_.quaternion()[1];
                double y = secondary_imustate->msg_.quaternion()[2];
                double z = secondary_imustate->msg_.quaternion()[3];

                secondary_imustate->msg_.rpy()[0] = atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y));
                secondary_imustate->msg_.rpy()[1] = asin(2 * (w * y - z * x));
                secondary_imustate->msg_.rpy()[2] = atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z));
            }

            if(secondary_imu_gyro_adr_ >= 0) {
                secondary_imustate->msg_.gyroscope()[0] = mj_data_->sensordata[secondary_imu_gyro_adr_ + 0];
                secondary_imustate->msg_.gyroscope()[1] = mj_data_->sensordata[secondary_imu_gyro_adr_ + 1];
                secondary_imustate->msg_.gyroscope()[2] = mj_data_->sensordata[secondary_imu_gyro_adr_ + 2];
            }

            if(secondary_imu_acc_adr_ >= 0) {
                secondary_imustate->msg_.accelerometer()[0] = mj_data_->sensordata[secondary_imu_acc_adr_ + 0];
                secondary_imustate->msg_.accelerometer()[1] = mj_data_->sensordata[secondary_imu_acc_adr_ + 1];
                secondary_imustate->msg_.accelerometer()[2] = mj_data_->sensordata[secondary_imu_acc_adr_ + 2];
            }

            secondary_imustate->unlockAndPublish();
        }

        // In practice, bmsstate is sent at a low frequency; here it is sent with the main loop
        bmsstate->unlockAndPublish();
    }

    using BmsState_t = unitree::robot::RealTimePublisher<unitree_hg::msg::dds_::BmsState_>;
    using IMUState_t = unitree::robot::RealTimePublisher<unitree_hg::msg::dds_::IMUState_>;
    std::unique_ptr<BmsState_t> bmsstate;
    std::unique_ptr<IMUState_t> secondary_imustate;
};
