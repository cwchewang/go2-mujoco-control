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

go2_control::KnownStepGeometry V2Geometry()
{
    return {false, 0.80, 0.05, 1.00, true};
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

bool CheckV2ProbeLatchesAtSwingEntry()
{
    const auto plan = go2_control::PlanKnownStepV2Crossing(
        V2Geometry(), {0.740, 0.0, 0.020}, {0.790, 0.0, 0.020},
        {0.860, 0.0, 0.020}, 0.028);
    return plan.crossing_latched && plan.planning_valid &&
           Near(plan.h_nom_m, 0.0) && Near(plan.h_probe_m, 0.05) &&
           Near(plan.rise_m, 0.05);
}

bool CheckV2FloorAndPlateauNoCrossing()
{
    const auto floor = go2_control::PlanKnownStepV2Crossing(
        V2Geometry(), {0.740, 0.0, 0.020}, {0.750, 0.0, 0.020},
        {0.760, 0.0, 0.020}, 0.028);
    const auto plateau = go2_control::PlanKnownStepV2Crossing(
        V2Geometry(), {0.900, 0.0, 0.070}, {1.000, 0.0, 0.070},
        {1.010, 0.0, 0.070}, 0.028);
    return !floor.crossing_latched && floor.planning_valid &&
           floor.planning_failure_code == go2_control::kKnownStepV2NotACrossing &&
           !plateau.crossing_latched && Near(plateau.rise_m, 0.0) &&
           Near(plateau.final_touchdown_world.z, 0.07);
}

bool CheckV2FrozenCrossingTarget()
{
    go2_control::CartesianWorldState state;
    state.have_prev = true;
    state.prev_stance.fill(true);
    state.stance_valid.fill(true);
    std::array<go2::Vec3, go2::kLegCount> feet{};
    for (auto &foot : feet)
        foot = {0.740, 0.0, 0.020};
    state.stance_anchor_world = feet;

    go2_control::CartesianWorldInput first;
    first.base = {0.650, 0.0, 0.0};
    first.actual_world_feet = feet;
    first.stand_body_feet = feet;
    first.phase = 0.750;
    first.duty_factor = 0.75;
    first.period_s = 0.60;
    first.v_cmd_mps = 0.15;
    first.vx_world = 0.15;
    first.world_heading = true;
    first.known_step_geometry = V2Geometry();
    std::array<go2::Vec3, go2::kLegCount> body_feet{};
    go2_control::ApplyCartesianWorldTrot(first, state, body_feet);
    const auto expected = state.swing_target_world[0];
    if (!state.known_step_v2_plan[0].crossing_latched)
        return false;

    auto later = first;
    later.base.x = 0.900;
    later.vx_world = 1.20;
    later.phase = 0.850;
    go2_control::ApplyCartesianWorldTrot(later, state, body_feet);
    const auto actual = state.swing_target_world[0];
    return actual.x == expected.x && actual.y == expected.y &&
           actual.z == expected.z;
}

bool CheckV2GeometryAndCorridor()
{
    const auto plan = go2_control::PlanKnownStepV2Crossing(
        V2Geometry(), {0.740, 0.0, 0.020}, {0.790, 0.0, 0.020},
        {0.860, 0.0, 0.020}, 0.028);
    if (!plan.planning_valid || !(0.0 < plan.s_entry &&
                                  plan.s_entry < plan.s_exit &&
                                  plan.s_exit < 1.0) ||
        plan.final_touchdown_world.x < 0.850 ||
        !Near(plan.final_touchdown_world.y,
              plan.ordinary_nominal_touchdown_world.y) ||
        !Near(plan.final_touchdown_world.z, 0.070))
        return false;

    for (int i = 0; i <= 10000; ++i)
    {
        const double phase = static_cast<double>(i) / 10000.0;
        const auto position = go2_control::KnownStepV2SwingTarget(plan, phase);
        if (position.x >= plan.x_entry_m - 1.0e-12 &&
            position.x <= plan.x_exit_m + 1.0e-12 &&
            position.z < plan.z_corridor_m - 1.0e-12)
            return false;
    }
    return true;
}

double PhaseAtProgress(double target)
{
    double lo = 0.0;
    double hi = 0.80;
    for (int i = 0; i < 80; ++i)
    {
        const double mid = 0.5 * (lo + hi);
        if (go2_control::HistoricalHorizontalProgress(mid) < target)
            lo = mid;
        else
            hi = mid;
    }
    return 0.5 * (lo + hi);
}

bool CheckV2BoundaryContinuity()
{
    const auto plan = go2_control::PlanKnownStepV2Crossing(
        V2Geometry(), {0.740, 0.0, 0.020}, {0.790, 0.0, 0.020},
        {0.860, 0.0, 0.020}, 0.028);
    const double delta = 1.0e-7;
    for (const double boundary : {plan.s_entry, plan.s_exit})
    {
        const double phase = PhaseAtProgress(boundary);
        const auto before = go2_control::KnownStepV2SwingTarget(
            plan, phase - delta);
        const auto after = go2_control::KnownStepV2SwingTarget(
            plan, phase + delta);
        const auto v_before = go2_control::KnownStepV2SwingVelocity(
            plan, phase - delta, 0.15);
        const auto v_after = go2_control::KnownStepV2SwingVelocity(
            plan, phase + delta, 0.15);
        if (!Near(before.z, after.z, 1.0e-8) ||
            !Near(v_before.z, v_after.z, 1.0e-5))
            return false;
    }
    return true;
}

bool CheckV2InvalidOrderingAndHistoricalFallback()
{
    const auto invalid = go2_control::PlanKnownStepV2Crossing(
        V2Geometry(), {0.780, 0.0, 0.020}, {0.810, 0.0, 0.020},
        {0.820, 0.0, 0.020}, 0.028);
    if (!invalid.crossing_latched || invalid.planning_valid ||
        invalid.planning_failure_code != go2_control::kKnownStepV2InvalidEdgeOrdering ||
        !Near(invalid.final_touchdown_world.x, 0.810) ||
        !Near(invalid.effective_lift_m, 0.028))
        return false;

    const auto non_crossing = go2_control::PlanKnownStepV2Crossing(
        V2Geometry(), {0.740, 0.0, 0.020}, {0.750, 0.0, 0.020},
        {0.760, 0.0, 0.020}, 0.028);
    const auto v2_position = go2_control::KnownStepV2SwingTarget(
        non_crossing, 0.40);
    const auto historical_position = go2_control::SwingWorldTarget(
        non_crossing.swing_start_world,
        non_crossing.final_touchdown_world, 0.40,
        non_crossing.effective_lift_m);
    const auto v2_velocity = go2_control::KnownStepV2SwingVelocity(
        non_crossing, 0.40, 0.15);
    const auto historical_velocity = go2_control::SwingWorldVelocity(
        non_crossing.swing_start_world,
        non_crossing.final_touchdown_world, 0.40,
        non_crossing.effective_lift_m, 0.15);
    return v2_position.x == historical_position.x &&
           v2_position.z == historical_position.z &&
           v2_velocity.x == historical_velocity.x &&
           v2_velocity.z == historical_velocity.z;
}

}  // namespace

int main()
{
    const bool checks[] = {
        CheckDisabledIdentity(),
        CheckFloorToFloor(),
        CheckFloorToPlateau(),
        CheckPlateauToPlateau(),
        CheckOutsideWidthIsFloor(),
        CheckNominalXYUnchanged(),
        CheckSharedEffectiveLiftForPositionAndVelocity(),
        CheckV2ProbeLatchesAtSwingEntry(),
        CheckV2FloorAndPlateauNoCrossing(),
        CheckV2FrozenCrossingTarget(),
        CheckV2GeometryAndCorridor(),
        CheckV2BoundaryContinuity(),
        CheckV2InvalidOrderingAndHistoricalFallback()};
    for (std::size_t i = 0; i < sizeof(checks) / sizeof(checks[0]); ++i)
        if (!checks[i])
            std::cerr << "failed check " << i << "\n";
    if (!std::all_of(std::begin(checks), std::end(checks), [](bool value) {
            return value;
        }))
    {
        std::cerr << "known-step terrain adapter checks failed\n";
        return 1;
    }
    std::cout << "known-step terrain adapter checks passed.\n";
    return 0;
}
