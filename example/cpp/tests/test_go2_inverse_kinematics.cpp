#include <array>
#include <cmath>
#include <iostream>

#include "clean_baseline.h"
#include "go2_inverse_kinematics.h"

namespace
{

bool Near(double actual, double expected, double tolerance = 1e-9)
{
    return std::abs(actual - expected) <= tolerance;
}

bool CheckRoundTrip(const std::array<double, go2::kJointCount> &source_joints)
{
    const auto source_feet = go2::AllFootPositions(source_joints);
    std::array<double, go2::kJointCount> solved_joints{};
    if (!go2::AllLegInverseKinematics(source_feet, solved_joints))
    {
        std::cerr << "Inverse kinematics rejected a reachable pose\n";
        return false;
    }

    const auto solved_feet = go2::AllFootPositions(solved_joints);
    for (std::size_t i = 0; i < source_feet.size(); ++i)
    {
        if (!Near(source_feet[i].x, solved_feet[i].x) ||
            !Near(source_feet[i].y, solved_feet[i].y) ||
            !Near(source_feet[i].z, solved_feet[i].z))
        {
            std::cerr << "FK/IK round-trip failed for leg " << i << "\n";
            return false;
        }
    }
    return true;
}

bool CheckClampedSwingDoesNotMoveStance()
{
    const std::array<double, go2::kJointCount> stand_pose = {
        0.00571868, 0.608813, -1.21763,
        -0.00571868, 0.608813, -1.21763,
        0.00571868, 0.608813, -1.21763,
        -0.00571868, 0.608813, -1.21763};
    const auto original_feet = go2::AllFootPositions(stand_pose);
    auto target_feet = original_feet;
    target_feet[1].x += 0.50;
    std::array<double, go2::kJointCount> solved_joints{};
    if (!go2::AllLegInverseKinematicsClamped(target_feet, solved_joints))
        return false;
    for (std::size_t leg = 0; leg < go2::kLegCount; ++leg)
    {
        if (leg == 1)
            continue;
        if (!Near(target_feet[leg].x, original_feet[leg].x) ||
            !Near(target_feet[leg].y, original_feet[leg].y) ||
            !Near(target_feet[leg].z, original_feet[leg].z))
        {
            std::cerr << "Clamped swing target moved a stance foot" << std::endl;
            return false;
        }
    }
    return true;
}

bool CheckBodyShiftTargets()
{
    const std::array<double, go2::kJointCount> stand_pose = {
        0.00571868, 0.608813, -1.21763,
        -0.00571868, 0.608813, -1.21763,
        0.00571868, 0.608813, -1.21763,
        -0.00571868, 0.608813, -1.21763};
    const auto stand_feet = go2::AllFootPositions(stand_pose);

    for (const go2::Vec3 body_shift : {
             go2::Vec3{-0.01, 0.01, 0.0},
             go2::Vec3{-0.02, 0.015, 0.0},
             go2::Vec3{-0.03, 0.02, 0.0}})
    {
        auto target_feet = stand_feet;
        for (auto &foot : target_feet)
        {
            foot.x -= body_shift.x;
            foot.y -= body_shift.y;
            foot.z -= body_shift.z;
        }

        std::array<double, go2::kJointCount> target_joints{};
        if (!go2::AllLegInverseKinematics(target_feet, target_joints))
        {
            std::cerr << "IK rejected a planned body-shift target\n";
            return false;
        }
        if (!CheckRoundTrip(target_joints))
        {
            return false;
        }
    }
    return true;
}

bool CheckCleanTargetBoundary()
{
    const std::array<double, go2::kJointCount> stand_pose = {
        0.00571868, 0.608813, -1.21763,
        -0.00571868, 0.608813, -1.21763,
        0.00571868, 0.608813, -1.21763,
        -0.00571868, 0.608813, -1.21763};
    const auto feasible_target = go2::AllFootPositions(stand_pose);
    std::array<double, go2::kJointCount> solved{};
    if (!go2_control::clean_baseline::ResolveFootTargetsToJointPositions(
            feasible_target, solved))
    {
        std::cerr << "Clean path rejected a feasible target\n";
        return false;
    }
    const auto solved_feet = go2::AllFootPositions(solved);
    for (std::size_t leg = 0; leg < go2::kLegCount; ++leg)
        if (!Near(solved_feet[leg].x, feasible_target[leg].x) ||
            !Near(solved_feet[leg].y, feasible_target[leg].y) ||
            !Near(solved_feet[leg].z, feasible_target[leg].z))
            return false;

    auto unreachable_target = feasible_target;
    unreachable_target[static_cast<std::size_t>(go2::Leg::FR)].x += 1.0;
    solved.fill(-99.0);
    if (go2_control::clean_baseline::ResolveFootTargetsToJointPositions(
            unreachable_target, solved))
    {
        std::cerr << "Clean path accepted an unreachable target\n";
        return false;
    }
    if (!Near(unreachable_target[0].x, feasible_target[0].x + 1.0))
        return false;

    // This target is analytically IK-solvable, but its calf angle is below
    // the authoritative MuJoCo lower limit (-2.7227 rad).
    auto joint_range_invalid_target = feasible_target;
    joint_range_invalid_target[static_cast<std::size_t>(go2::Leg::FR)] =
        go2::FootPosition(go2::Leg::FR, 0.0, 0.6, -2.75);
    std::array<double, go2::kJointCount> direct_solution{};
    if (!go2::AllLegInverseKinematics(
            joint_range_invalid_target, direct_solution) ||
        go2::JointPositionsWithinMuJoCoLimits(direct_solution))
    {
        std::cerr << "Joint-range-invalid fixture is not valid\n";
        return false;
    }
    if (go2_control::clean_baseline::ResolveFootTargetsToJointPositions(
            joint_range_invalid_target, solved))
    {
        std::cerr << "Clean path moved/accepted a joint-range-invalid target\n";
        return false;
    }
    return true;
}

} // namespace

int main()
{
    const std::array<double, go2::kJointCount> stand_pose = {
        0.00571868, 0.608813, -1.21763,
        -0.00571868, 0.608813, -1.21763,
        0.00571868, 0.608813, -1.21763,
        -0.00571868, 0.608813, -1.21763};

    if (!CheckRoundTrip(stand_pose) || !CheckBodyShiftTargets() ||
        !CheckClampedSwingDoesNotMoveStance() || !CheckCleanTargetBoundary())
    {
        return 1;
    }

    std::cout << "Inverse kinematics checks passed for stand and body-shift targets.\n";
    return 0;
}
