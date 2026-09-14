#pragma once

#include <unitree/idl/go2/LowCmd_.hpp>
#include <unitree/idl/go2/LowState_.hpp>
#include <unitree/idl/go2/SportModeState_.hpp>

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>

namespace phase1_boundary_trace
{
inline bool Enabled()
{
    const char *value = std::getenv("TROT_PHASE1_BOUNDARY_TRACE");
    return value != nullptr &&
        (std::string(value) == "1" || std::string(value) == "true");
}

inline std::string BasePath()
{
    const char *value = std::getenv("TROT_PHASE1_BOUNDARY_TRACE_BASE");
    return value == nullptr ? std::string{} : std::string(value);
}

inline std::uint32_t StartTick()
{
    const char *value = std::getenv("TROT_PHASE1_BOUNDARY_TRACE_START_TICK");
    return value == nullptr ? 11800u
                            : static_cast<std::uint32_t>(std::strtoul(value, nullptr, 10));
}

inline std::uint32_t EndTick()
{
    const char *value = std::getenv("TROT_PHASE1_BOUNDARY_TRACE_END_TICK");
    return value == nullptr ? 12600u
                            : static_cast<std::uint32_t>(std::strtoul(value, nullptr, 10));
}

inline bool InWindow(std::uint32_t tick)
{
    return tick >= StartTick() && tick <= EndTick();
}

using Bytes = std::vector<std::uint8_t>;

template <typename T, bool Floating = std::is_floating_point_v<T>>
struct ScalarBits;

template <typename T>
struct ScalarBits<T, true>
{
    using type = std::conditional_t<
        sizeof(T) == 4, std::uint32_t, std::uint64_t>;
};

template <typename T>
struct ScalarBits<T, false>
{
    using type = std::make_unsigned_t<T>;
};

template <typename T>
inline void AppendScalar(Bytes &out, T value)
{
    static_assert(std::is_arithmetic_v<T>);
    using U = typename ScalarBits<T>::type;
    U bits{};
    static_assert(sizeof(bits) == sizeof(T));
    std::memcpy(&bits, &value, sizeof(bits));
    for (std::size_t i = 0; i < sizeof(bits); ++i)
        out.push_back(static_cast<std::uint8_t>(bits >> (8 * i)));
}

inline void AppendFloat(Bytes &out, float value)
{
    AppendScalar(out, value);
}

inline void AppendInt16(Bytes &out, std::int16_t value)
{
    AppendScalar(out, value);
}

inline Bytes CanonicalLowState(
    const unitree_go::msg::dds_::LowState_ &state)
{
    Bytes out;
    AppendScalar(out, static_cast<std::uint32_t>(state.tick()));
    for (int i = 0; i < 12; ++i)
    {
        AppendFloat(out, static_cast<float>(state.motor_state()[i].q()));
        AppendFloat(out, static_cast<float>(state.motor_state()[i].dq()));
        AppendFloat(out, static_cast<float>(state.motor_state()[i].tau_est()));
    }
    for (int i = 0; i < 4; ++i)
        AppendFloat(out, static_cast<float>(state.imu_state().quaternion()[i]));
    for (int i = 0; i < 3; ++i)
        AppendFloat(out, static_cast<float>(state.imu_state().rpy()[i]));
    for (int i = 0; i < 3; ++i)
        AppendFloat(out, static_cast<float>(state.imu_state().gyroscope()[i]));
    for (int i = 0; i < 3; ++i)
        AppendFloat(out, static_cast<float>(state.imu_state().accelerometer()[i]));
    for (int i = 0; i < 4; ++i)
        AppendInt16(out, static_cast<std::int16_t>(state.foot_force()[i]));
    return out;
}

inline Bytes CanonicalHighState(
    const unitree_go::msg::dds_::SportModeState_ &state)
{
    Bytes out;
    for (int i = 0; i < 3; ++i)
        AppendFloat(out, static_cast<float>(state.position()[i]));
    for (int i = 0; i < 3; ++i)
        AppendFloat(out, static_cast<float>(state.velocity()[i]));
    return out;
}

inline Bytes CanonicalLowCmd(
    const unitree_go::msg::dds_::LowCmd_ &cmd)
{
    Bytes out;
    for (int i = 0; i < 12; ++i)
    {
        AppendFloat(out, static_cast<float>(cmd.motor_cmd()[i].q()));
        AppendFloat(out, static_cast<float>(cmd.motor_cmd()[i].dq()));
        AppendFloat(out, static_cast<float>(cmd.motor_cmd()[i].kp()));
        AppendFloat(out, static_cast<float>(cmd.motor_cmd()[i].kd()));
        AppendFloat(out, static_cast<float>(cmd.motor_cmd()[i].tau()));
    }
    return out;
}

inline std::string Hex(const Bytes &bytes)
{
    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (std::uint8_t byte : bytes)
        out << std::setw(2) << static_cast<unsigned>(byte);
    return out.str();
}

inline std::string Hash(const Bytes &bytes)
{
    std::uint64_t value = 1469598103934665603ULL;
    for (std::uint8_t byte : bytes)
    {
        value ^= byte;
        value *= 1099511628211ULL;
    }
    std::ostringstream out;
    out << std::hex << std::setfill('0') << std::setw(16) << value;
    return out.str();
}
}  // namespace phase1_boundary_trace
