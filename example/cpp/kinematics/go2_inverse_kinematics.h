// Go2 leg inverse kinematics (foot target -> joint angles).
#pragma once

#include <algorithm>
#include <array>
#include <cmath>

#include "go2_forward_kinematics.h"

namespace go2
{

struct LegJointPositions
{
    double hip = 0.0;
    double thigh = 0.0;
    double calf = 0.0;
};

// These are the authoritative ranges in unitree_robots/go2/go2.xml.  Keep
// them beside the analytical IK so a clean target can be rejected without
// projecting it to a different point.  The rear thigh range is intentionally
// distinct from the front thigh range.
struct JointRange
{
    double lower;
    double upper;
};

inline JointRange JointRangeFor(Leg leg, std::size_t joint_in_leg)
{
    static constexpr JointRange kCommonRanges[kJointsPerLeg] = {
        {-1.0472, 1.0472},
        {0.0, 0.0},
        {-2.7227, -0.83776},
    };
    static constexpr JointRange kFrontThigh{-1.5708, 3.4907};
    static constexpr JointRange kRearThigh{-0.5236, 4.5379};
    if (joint_in_leg == 1)
        return leg == Leg::FR || leg == Leg::FL
            ? kFrontThigh : kRearThigh;
    return joint_in_leg < kJointsPerLeg
        ? kCommonRanges[joint_in_leg]
        : JointRange{1.0, 0.0};
}

inline bool JointPositionsWithinMuJoCoLimits(
    const std::array<double, kJointCount> &joint_positions,
    double tolerance = 1.0e-9)
{
    if (!std::isfinite(tolerance) || tolerance < 0.0)
        return false;
    for (std::size_t leg = 0; leg < kLegCount; ++leg)
    {
        for (std::size_t joint = 0; joint < kJointsPerLeg; ++joint)
        {
            const double value = joint_positions[leg * kJointsPerLeg + joint];
            const JointRange range = JointRangeFor(
                static_cast<Leg>(leg), joint);
            if (!std::isfinite(value) ||
                value < range.lower - tolerance ||
                value > range.upper + tolerance)
                return false;
        }
    }
    return true;
}

inline bool LegInverseKinematics(
    Leg leg,
    const Vec3 &foot_position,
    LegJointPositions &joint_positions)
{
    const LegGeometry geometry = Geometry(leg);
    const double x = foot_position.x - geometry.hip_x;
    const double y = foot_position.y - geometry.hip_y;
    const double z = foot_position.z;

    const double leg_z_squared =
        y * y + z * z - geometry.hip_link_y * geometry.hip_link_y;
    if (leg_z_squared < -1e-12)
    {
        return false;
    }

    // The normal standing solution places the thigh joint below the hip link.
    const double leg_z = -std::sqrt(std::max(0.0, leg_z_squared));
    const double q_hip =
        std::atan2(z, y) - std::atan2(leg_z, geometry.hip_link_y);

    const double planar_distance_squared = x * x + leg_z * leg_z;
    const double cosine_calf =
        (planar_distance_squared -
         geometry.thigh_length * geometry.thigh_length -
         geometry.calf_length * geometry.calf_length) /
        (2.0 * geometry.thigh_length * geometry.calf_length);
    if (cosine_calf < -1.0 - 1e-12 || cosine_calf > 1.0 + 1e-12)
    {
        return false;
    }

    // Go2's normal knee configuration uses the negative knee-angle branch.
    const double q_calf = -std::acos(std::clamp(cosine_calf, -1.0, 1.0));
    const double q_thigh =
        std::atan2(-x, -leg_z) -
        std::atan2(
            geometry.calf_length * std::sin(q_calf),
            geometry.thigh_length +
                geometry.calf_length * std::cos(q_calf));

    joint_positions = {q_hip, q_thigh, q_calf};
    return true;
}

inline bool AllLegInverseKinematics(
    const std::array<Vec3, kLegCount> &foot_positions,
    std::array<double, kJointCount> &joint_positions)
{
    for (std::size_t leg_index = 0; leg_index < kLegCount; ++leg_index)
    {
        LegJointPositions leg_joints;
        if (!LegInverseKinematics(
                static_cast<Leg>(leg_index),
                foot_positions[leg_index],
                leg_joints))
        {
            return false;
        }

        const std::size_t joint_index = leg_index * kJointsPerLeg;
        joint_positions[joint_index] = leg_joints.hip;
        joint_positions[joint_index + 1] = leg_joints.thigh;
        joint_positions[joint_index + 2] = leg_joints.calf;
    }
    return true;
}

// Clean-baseline target boundary: solve direct IK first, then reject any
// solution outside the MuJoCo joint ranges.  This deliberately does not
// modify foot_positions or project an infeasible target.
inline bool AllLegInverseKinematicsWithinMuJoCoLimits(
    const std::array<Vec3, kLegCount> &foot_positions,
    std::array<double, kJointCount> &joint_positions,
    double tolerance = 1.0e-9)
{
    std::array<double, kJointCount> candidate{};
    if (!AllLegInverseKinematics(foot_positions, candidate) ||
        !JointPositionsWithinMuJoCoLimits(candidate, tolerance))
        return false;
    joint_positions = candidate;
    return true;
}

// LEGACY compatibility boundary.  This function may project a requested foot
// target and is never part of the clean-baseline or future terrain-actuation
// contract.
inline bool AllLegInverseKinematicsClamped(
    std::array<Vec3, kLegCount> &foot_positions,
    std::array<double, kJointCount> &joint_positions)
{
    // Clamp each leg independently. A single unreachable swing target must
    // not retract otherwise-valid stance feet, because those feet are also
    // the WBC measured support anchors during a terrain transfer.
    for (std::size_t leg_index = 0; leg_index < kLegCount; ++leg_index)
    {
        const auto leg = static_cast<Leg>(leg_index);
        LegJointPositions leg_joints;
        bool reachable = LegInverseKinematics(
            leg, foot_positions[leg_index], leg_joints);
        for (int iter = 0; !reachable && iter < 16; ++iter)
        {
            const LegGeometry geometry = Geometry(leg);
            foot_positions[leg_index].x = geometry.hip_x +
                0.88 * (foot_positions[leg_index].x - geometry.hip_x);
            foot_positions[leg_index].y = geometry.hip_y +
                0.88 * (foot_positions[leg_index].y - geometry.hip_y);
            reachable = LegInverseKinematics(
                leg, foot_positions[leg_index], leg_joints);
        }
        if (!reachable)
            return false;
        const std::size_t joint_index = leg_index * kJointsPerLeg;
        joint_positions[joint_index] = leg_joints.hip;
        joint_positions[joint_index + 1] = leg_joints.thigh;
        joint_positions[joint_index + 2] = leg_joints.calf;
    }
    return true;
}

} // namespace go2
