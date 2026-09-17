#pragma once

// Small, explicit seams for the opt-in clean research baseline.  Historical
// controller paths remain free to use their existing clamp/overlay behavior;
// this header only provides the strict target and final-torque boundaries.

#include <algorithm>
#include <array>
#include <cmath>

#include "go2_inverse_kinematics.h"

namespace go2_control::clean_baseline
{

inline bool ResolveFootTargetsToJointPositions(
    const std::array<go2::Vec3, go2::kLegCount> &requested_targets,
    std::array<double, go2::kJointCount> &joint_positions)
{
    std::array<double, go2::kJointCount> candidate{};
    if (!go2::AllLegInverseKinematicsWithinMuJoCoLimits(
            requested_targets, candidate))
        return false;
    joint_positions = candidate;
    return true;
}

inline double ApplyFinalTorqueSafetyEnvelope(
    double accepted_torque_nm, double ramp, double limit_nm)
{
    if (!std::isfinite(accepted_torque_nm) ||
        !std::isfinite(ramp) || !std::isfinite(limit_nm) ||
        limit_nm < 0.0)
        return 0.0;
    const double ramped = std::clamp(ramp, 0.0, 1.0) * accepted_torque_nm;
    return std::clamp(ramped, -limit_nm, limit_nm);
}

}  // namespace go2_control::clean_baseline
