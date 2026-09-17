#include <cmath>
#include <iostream>

#include "clean_baseline.h"

namespace
{

bool Check(bool ok, const char *message)
{
    if (!ok)
        std::cerr << message << "\n";
    return ok;
}

}  // namespace

int main()
{
    // The clean command boundary permits only the documented final ramp and
    // absolute safety envelope; there is no post-QP force/Cartesian term.
    const double accepted = 2.0;
    const double command =
        go2_control::clean_baseline::ApplyFinalTorqueSafetyEnvelope(
            accepted, 0.5, 0.75);
    const double negative_command =
        go2_control::clean_baseline::ApplyFinalTorqueSafetyEnvelope(
            -2.0, 0.5, 0.75);
    const bool passed =
        Check(std::abs(command - 0.75) < 1.0e-12,
              "clean torque envelope added or removed an unexpected term") &&
        Check(std::abs(negative_command + 0.75) < 1.0e-12,
              "clean torque envelope negative limit") &&
        Check(
            go2_control::clean_baseline::ApplyFinalTorqueSafetyEnvelope(
                0.4, 1.0, 0.75) == 0.4,
            "clean torque envelope changed an in-range accepted torque");
    if (!passed)
        return 1;
    std::cout << "clean baseline torque boundary checks passed.\n";
    return 0;
}
