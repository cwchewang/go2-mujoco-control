#pragma once

#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>

namespace go2_highstate_pairing
{
constexpr std::size_t kMotorStateFieldCount = 7;
constexpr std::uint32_t kMarker = 0x48535031u; // HSP1
constexpr std::uint32_t kVersion = 1u;

using MotorStateFields = std::array<float, kMotorStateFieldCount>;

struct Payload
{
    std::array<float, 3> position{};
    std::array<float, 3> velocity{};
    std::uint32_t source_tick = 0;
};

struct DecodeResult
{
    bool valid = false;
    Payload payload{};
};

enum class Resolution
{
    kNoHighState,
    kUseAsync,
    kUsePaired,
    kFailClosed,
};

inline bool EnvEnabled(const char *name)
{
    const char *value = std::getenv(name);
    return value != nullptr &&
           (std::string(value) == "1" || std::string(value) == "true");
}

inline bool Enabled()
{
    return EnvEnabled("SIM_LOCKSTEP") &&
           EnvEnabled("TROT_LOCKSTEP_PAIRED_HIGHSTATE");
}

inline float BitsToFloat(std::uint32_t bits)
{
    float value = 0.0f;
    static_assert(sizeof(value) == sizeof(bits));
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

inline std::uint32_t FloatToBits(float value)
{
    std::uint32_t bits = 0;
    static_assert(sizeof(value) == sizeof(bits));
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

inline std::array<MotorStateFields, 2> Pack(const Payload &payload)
{
    std::array<MotorStateFields, 2> slots{};
    slots[0][0] = payload.position[0];
    slots[0][1] = payload.position[1];
    slots[0][2] = payload.position[2];
    slots[0][3] = payload.velocity[0];
    slots[0][4] = payload.velocity[1];
    slots[0][5] = payload.velocity[2];
    slots[0][6] = BitsToFloat(kMarker);
    slots[1][0] = BitsToFloat(kVersion);
    slots[1][1] = BitsToFloat(payload.source_tick);
    slots[1][2] = BitsToFloat(~payload.source_tick);
    return slots;
}

inline DecodeResult Decode(
    const MotorStateFields &slot18,
    const MotorStateFields &slot19,
    std::uint32_t lowstate_tick)
{
    DecodeResult result;
    result.payload.position = {slot18[0], slot18[1], slot18[2]};
    result.payload.velocity = {slot18[3], slot18[4], slot18[5]};
    result.payload.source_tick = FloatToBits(slot19[1]);
    if (FloatToBits(slot18[6]) != kMarker ||
        FloatToBits(slot19[0]) != kVersion ||
        result.payload.source_tick != lowstate_tick ||
        FloatToBits(slot19[2]) != ~result.payload.source_tick)
        return result;
    result.valid = true;
    return result;
}

inline Resolution Resolve(
    bool paired_mode,
    bool have_async_highstate,
    bool paired_payload_valid)
{
    if (!paired_mode)
        return have_async_highstate
            ? Resolution::kUseAsync
            : Resolution::kNoHighState;
    return paired_payload_valid
        ? Resolution::kUsePaired
        : Resolution::kFailClosed;
}

template <typename MotorState>
inline MotorStateFields ReadMotorStateFields(const MotorState &state)
{
    return {
        static_cast<float>(state.q()),
        static_cast<float>(state.dq()),
        static_cast<float>(state.ddq()),
        static_cast<float>(state.tau_est()),
        static_cast<float>(state.q_raw()),
        static_cast<float>(state.dq_raw()),
        static_cast<float>(state.ddq_raw())};
}

template <typename MotorState>
inline void WriteMotorStateFields(
    MotorState &state, const MotorStateFields &fields)
{
    state.q() = fields[0];
    state.dq() = fields[1];
    state.ddq() = fields[2];
    state.tau_est() = fields[3];
    state.q_raw() = fields[4];
    state.dq_raw() = fields[5];
    state.ddq_raw() = fields[6];
}
} // namespace go2_highstate_pairing
