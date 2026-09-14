#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>

#include "highstate_pairing_sideband.h"

namespace
{
int failures = 0;

void Check(bool condition, const char *what)
{
    if (!condition)
    {
        std::fprintf(stderr, "FAIL: %s\n", what);
        ++failures;
    }
}

bool SameBits(float left, float right)
{
    return std::memcmp(&left, &right, sizeof(left)) == 0;
}

void TestPackUnpackExact()
{
    go2_highstate_pairing::Payload expected;
    expected.position = {1.25f, -2.5f, 3.75f};
    expected.velocity = {-4.5f, 5.25f, -6.125f};
    expected.source_tick = 12302u;
    const auto slots = go2_highstate_pairing::Pack(expected);
    const auto decoded = go2_highstate_pairing::Decode(
        slots[0], slots[1], expected.source_tick);
    Check(decoded.valid, "valid sideband decodes");
    for (std::size_t i = 0; i < 3; ++i)
    {
        Check(SameBits(decoded.payload.position[i], expected.position[i]),
              "position float bits preserved");
        Check(SameBits(decoded.payload.velocity[i], expected.velocity[i]),
              "velocity float bits preserved");
    }
    Check(decoded.payload.source_tick == expected.source_tick,
          "decoded source tick preserved exactly");
}

void TestTickValidation()
{
    go2_highstate_pairing::Payload expected;
    expected.source_tick = 12302u;
    auto slots = go2_highstate_pairing::Pack(expected);
    Check(!go2_highstate_pairing::Decode(
              slots[0], slots[1], expected.source_tick + 2).valid,
          "source tick mismatch fails closed");
}

void TestMarkerAndVersionValidation()
{
    go2_highstate_pairing::Payload expected;
    expected.source_tick = 12302u;
    auto slots = go2_highstate_pairing::Pack(expected);
    slots[0][6] = go2_highstate_pairing::BitsToFloat(0u);
    Check(!go2_highstate_pairing::Decode(
              slots[0], slots[1], expected.source_tick).valid,
          "marker mismatch fails closed");
    slots = go2_highstate_pairing::Pack(expected);
    slots[1][0] = go2_highstate_pairing::BitsToFloat(2u);
    Check(!go2_highstate_pairing::Decode(
              slots[0], slots[1], expected.source_tick).valid,
          "version mismatch fails closed");
}

void TestFlagOffSelection()
{
    Check(
        go2_highstate_pairing::Resolve(false, true, false) ==
            go2_highstate_pairing::Resolution::kUseAsync,
        "paired mode disabled preserves asynchronous HighState");
    Check(
        go2_highstate_pairing::Resolve(false, false, false) ==
            go2_highstate_pairing::Resolution::kNoHighState,
        "paired mode disabled preserves no-HighState behavior");
}

void TestSlotsZeroThroughSeventeenUntouched()
{
    std::array<go2_highstate_pairing::MotorStateFields, 20> states{};
    for (std::size_t motor = 0; motor < 20; ++motor)
        for (std::size_t field = 0;
             field < go2_highstate_pairing::kMotorStateFieldCount; ++field)
            states[motor][field] =
                static_cast<float>(100.0 + motor * 10.0 + field);
    const auto before = states;
    go2_highstate_pairing::Payload payload;
    payload.source_tick = 12302u;
    const auto slots = go2_highstate_pairing::Pack(payload);
    states[18] = slots[0];
    states[19] = slots[1];
    for (std::size_t motor = 0; motor < 18; ++motor)
        for (std::size_t field = 0;
             field < go2_highstate_pairing::kMotorStateFieldCount; ++field)
            Check(SameBits(states[motor][field], before[motor][field]),
                  "motor_state slots 0..17 unchanged");
}
} // namespace

int main()
{
    TestPackUnpackExact();
    TestTickValidation();
    TestMarkerAndVersionValidation();
    TestFlagOffSelection();
    TestSlotsZeroThroughSeventeenUntouched();
    if (failures != 0)
    {
        std::fprintf(stderr, "highstate_pairing_sideband: %d failure(s)\n",
                     failures);
        return 1;
    }
    std::printf("highstate_pairing_sideband: all checks passed\n");
    return 0;
}
