#pragma once

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>

#include "go2_forward_kinematics.h"

namespace go2_control
{

struct KnownStepGeometry
{
    bool enabled = false;
    double edge_x_m = 0.80;
    double height_m = 0.05;
    double half_width_y_m = 1.00;
};

inline double KnownStepEnvDouble(const char *name, double fallback)
{
    const char *value = std::getenv(name);
    if (value == nullptr || value[0] == '\0')
        return fallback;
    char *end = nullptr;
    const double parsed = std::strtod(value, &end);
    return end == value ? fallback : parsed;
}

inline bool KnownStepEnvEnabled()
{
    const char *value = std::getenv("TROT_KNOWN_STEP_TRAVERSAL");
    return value != nullptr && std::strcmp(value, "1") == 0;
}

inline KnownStepGeometry KnownStepGeometryFromEnv()
{
    return {
        KnownStepEnvEnabled(),
        KnownStepEnvDouble("TROT_KNOWN_STEP_EDGE_X_M", 0.80),
        KnownStepEnvDouble("TROT_KNOWN_STEP_HEIGHT_M", 0.05),
        KnownStepEnvDouble("TROT_KNOWN_STEP_HALF_WIDTH_Y_M", 1.00)};
}

inline double KnownStepTerrainHeight(
    const KnownStepGeometry &geometry, double x_m, double y_m)
{
    if (std::abs(y_m) > geometry.half_width_y_m)
        return 0.0;
    return x_m < geometry.edge_x_m ? 0.0 : geometry.height_m;
}

struct KnownStepAdaptation
{
    go2::Vec3 nominal_touchdown_world{};
    go2::Vec3 final_touchdown_world{};
    double h0_m = 0.0;
    double h1_m = 0.0;
    double rise_m = 0.0;
    double effective_lift_m = 0.0;
    bool adaptation_active = false;
};

inline KnownStepAdaptation AdaptKnownStepTouchdown(
    const KnownStepGeometry &geometry,
    const go2::Vec3 &swing_start_world,
    const go2::Vec3 &nominal_touchdown_world,
    double base_foot_lift_m)
{
    KnownStepAdaptation out;
    out.nominal_touchdown_world = nominal_touchdown_world;
    out.final_touchdown_world = nominal_touchdown_world;
    out.h0_m = KnownStepTerrainHeight(
        geometry, swing_start_world.x, swing_start_world.y);
    out.h1_m = KnownStepTerrainHeight(
        geometry, nominal_touchdown_world.x, nominal_touchdown_world.y);
    out.rise_m = out.h1_m - out.h0_m;
    out.effective_lift_m = base_foot_lift_m;
    if (geometry.enabled && out.rise_m != 0.0)
    {
        out.final_touchdown_world.z =
            swing_start_world.z + out.rise_m;
        out.effective_lift_m = std::max(
            base_foot_lift_m, std::max(0.0, out.rise_m) + 0.030);
        out.adaptation_active = true;
    }
    return out;
}

}  // namespace go2_control
