#include <cmath>
#include <iostream>

#include "cartesian_world_trot.h"

namespace
{

bool Near(double actual, double expected, double tolerance = 1e-12)
{
    return std::abs(actual - expected) <= tolerance;
}

go2_control::KnownStepGeometry EnabledGeometry()
{
    return {true, 0.80, 0.05, 1.00};
}

bool CheckDisabledIdentity()
{
    const go2::Vec3 p0{0.75, 0.10, 0.02};
    const go2::Vec3 p1{0.90, 0.10, 0.02};
    const auto result = go2_control::AdaptKnownStepTouchdown(
        {false, 0.80, 0.05, 1.00}, p0, p1, 0.028);
    return result.final_touchdown_world.x == p1.x &&
           result.final_touchdown_world.y == p1.y &&
           result.final_touchdown_world.z == p1.z &&
           Near(result.effective_lift_m, 0.028) &&
           !result.adaptation_active;
}

bool CheckFloorToFloor()
{
    const auto result = go2_control::AdaptKnownStepTouchdown(
        EnabledGeometry(), {0.70, 0.0, 0.02}, {0.75, 0.0, 0.02}, 0.028);
    return Near(result.h0_m, 0.0) && Near(result.h1_m, 0.0) &&
           Near(result.rise_m, 0.0) &&
           Near(result.final_touchdown_world.z, 0.02) &&
           Near(result.effective_lift_m, 0.028) &&
           !result.adaptation_active;
}

bool CheckFloorToPlateau()
{
    const go2::Vec3 p0{0.75, 0.0, 0.02};
    const go2::Vec3 p1{0.90, 0.0, 0.02};
    const auto result = go2_control::AdaptKnownStepTouchdown(
        EnabledGeometry(), p0, p1, 0.028);
    return Near(result.h0_m, 0.0) && Near(result.h1_m, 0.05) &&
           Near(result.rise_m, 0.05) &&
           Near(result.final_touchdown_world.x, p1.x) &&
           Near(result.final_touchdown_world.y, p1.y) &&
           Near(result.final_touchdown_world.z, 0.07) &&
           Near(result.effective_lift_m, 0.080) &&
           result.adaptation_active;
}

bool CheckPlateauToPlateau()
{
    const auto result = go2_control::AdaptKnownStepTouchdown(
        EnabledGeometry(), {0.90, 0.0, 0.07}, {1.00, 0.0, 0.07}, 0.028);
    return Near(result.rise_m, 0.0) &&
           Near(result.final_touchdown_world.z, 0.07) &&
           Near(result.effective_lift_m, 0.028) &&
           !result.adaptation_active;
}

bool CheckOutsideWidthIsFloor()
{
    const auto result = go2_control::AdaptKnownStepTouchdown(
        EnabledGeometry(), {0.75, 1.01, 0.02}, {0.90, 1.01, 0.02}, 0.028);
    return Near(result.h0_m, 0.0) && Near(result.h1_m, 0.0) &&
           Near(result.rise_m, 0.0) &&
           Near(go2_control::KnownStepTerrainHeight(
                    EnabledGeometry(), 0.80, 1.01),
                0.0);
}

bool CheckNominalXYUnchanged()
{
    const go2::Vec3 nominal{0.93, -0.20, 0.11};
    const auto result = go2_control::AdaptKnownStepTouchdown(
        EnabledGeometry(), {0.75, -0.20, 0.02}, nominal, 0.028);
    return result.final_touchdown_world.x == nominal.x &&
           result.final_touchdown_world.y == nominal.y;
}

bool CheckSharedEffectiveLiftForPositionAndVelocity()
{
    const auto result = go2_control::AdaptKnownStepTouchdown(
        EnabledGeometry(), {0.75, 0.0, 0.02}, {0.90, 0.0, 0.02}, 0.028);
    const go2::Vec3 position = go2_control::SwingWorldTarget(
        {0.75, 0.0, 0.02}, result.final_touchdown_world, 0.40,
        result.effective_lift_m);
    const go2::Vec3 velocity = go2_control::SwingWorldVelocity(
        {0.75, 0.0, 0.02}, result.final_touchdown_world, 0.40,
        result.effective_lift_m, 0.15);
    const go2::Vec3 position_base = go2_control::SwingWorldTarget(
        {0.75, 0.0, 0.02}, result.final_touchdown_world, 0.40, 0.028);
    const go2::Vec3 velocity_base = go2_control::SwingWorldVelocity(
        {0.75, 0.0, 0.02}, result.final_touchdown_world, 0.40, 0.028, 0.15);
    return position.z > position_base.z + 0.04 &&
           velocity.z > velocity_base.z + 0.04;
}

}  // namespace

int main()
{
    if (!CheckDisabledIdentity() ||
        !CheckFloorToFloor() ||
        !CheckFloorToPlateau() ||
        !CheckPlateauToPlateau() ||
        !CheckOutsideWidthIsFloor() ||
        !CheckNominalXYUnchanged() ||
        !CheckSharedEffectiveLiftForPositionAndVelocity())
    {
        std::cerr << "known-step terrain adapter checks failed\n";
        return 1;
    }
    std::cout << "known-step terrain adapter checks passed.\n";
    return 0;
}
