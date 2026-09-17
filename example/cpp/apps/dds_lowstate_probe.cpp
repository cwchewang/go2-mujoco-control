#include <unitree/idl/go2/LowState_.hpp>
#include <unitree/robot/channel/channel_factory.hpp>
#include <unitree/robot/channel/channel_subscriber.hpp>

#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstdint>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>

namespace
{

using LowState = unitree_go::msg::dds_::LowState_;
constexpr const char *kTopic = "rt/lowstate";

struct Options
{
    int domain_id = -1;
    std::string interface_name = "lo";
    std::size_t minimum_samples = 10;
    double timeout_s = 10.0;
    std::string evidence_path;
};

void PrintUsage(const char *program)
{
    std::cout
        << "Usage: " << program
        << " --domain-id N [--interface NAME] [--samples N]"
        << " [--timeout-s S] [--evidence PATH]\n";
}

bool ParsePositiveInteger(const std::string &value, std::size_t *out)
{
    try
    {
        std::size_t consumed = 0;
        const unsigned long long parsed = std::stoull(value, &consumed);
        if (consumed != value.size() || parsed == 0)
            return false;
        *out = static_cast<std::size_t>(parsed);
        return true;
    }
    catch (const std::exception &)
    {
        return false;
    }
}

bool ParseOptions(int argc, char **argv, Options *options)
{
    for (int i = 1; i < argc; ++i)
    {
        const std::string argument = argv[i];
        auto require_value = [&](const char *name, std::string *value) {
            if (i + 1 >= argc)
            {
                std::cerr << name << " requires a value\n";
                return false;
            }
            *value = argv[++i];
            return true;
        };

        if (argument == "--help" || argument == "-h")
        {
            return false;
        }
        if (argument == "--domain-id")
        {
            std::string value;
            if (!require_value("--domain-id", &value))
                return false;
            try
            {
                std::size_t consumed = 0;
                options->domain_id = std::stoi(value, &consumed);
                if (consumed != value.size())
                    return false;
            }
            catch (const std::exception &)
            {
                return false;
            }
            continue;
        }
        if (argument == "--interface")
        {
            if (!require_value("--interface", &options->interface_name))
                return false;
            continue;
        }
        if (argument == "--samples")
        {
            std::string value;
            if (!require_value("--samples", &value) ||
                !ParsePositiveInteger(value, &options->minimum_samples))
                return false;
            continue;
        }
        if (argument == "--timeout-s")
        {
            std::string value;
            if (!require_value("--timeout-s", &value))
                return false;
            try
            {
                std::size_t consumed = 0;
                options->timeout_s = std::stod(value, &consumed);
                if (consumed != value.size() || !std::isfinite(options->timeout_s) ||
                    options->timeout_s <= 0.0)
                    return false;
            }
            catch (const std::exception &)
            {
                return false;
            }
            continue;
        }
        if (argument == "--evidence")
        {
            if (!require_value("--evidence", &options->evidence_path))
                return false;
            continue;
        }

        std::cerr << "Unknown argument: " << argument << "\n";
        return false;
    }

    if (options->domain_id < 0 || options->domain_id > 232 ||
        options->interface_name.empty())
    {
        return false;
    }
    return true;
}

class LowStateProbe
{
public:
    LowStateProbe(const Options &options) : options_(options) {}

    int Run()
    {
        using unitree::robot::ChannelFactory;
        using unitree::robot::ChannelSubscriber;

        std::cout << "DDS_PROBE_CONFIG domain_id=" << options_.domain_id
                  << " interface=" << options_.interface_name
                  << " topic=" << kTopic
                  << " publishes_lowcmd=false\n";

        ChannelFactory::Instance()->Init(
            options_.domain_id, options_.interface_name);
        subscriber_ = std::make_shared<ChannelSubscriber<LowState>>(kTopic);
        subscriber_->InitChannel(
            std::bind(&LowStateProbe::OnLowState, this, std::placeholders::_1),
            1);

        const auto deadline = std::chrono::steady_clock::now() +
            std::chrono::duration<double>(options_.timeout_s);
        {
            std::unique_lock<std::mutex> lock(mutex_);
            condition_.wait_until(lock, deadline, [&]() {
                return valid_samples_ >= options_.minimum_samples;
            });
        }

        const bool success = valid_samples_ >= options_.minimum_samples;
        const std::size_t valid_samples = valid_samples_;
        const std::uint32_t first_tick = first_tick_;
        const std::uint32_t last_tick = last_tick_;
        subscriber_->CloseChannel();
        subscriber_.reset();
        ChannelFactory::Instance()->Release();

        if (!options_.evidence_path.empty())
        {
            std::ofstream evidence(options_.evidence_path);
            if (!evidence)
            {
                std::cerr << "Unable to write probe evidence: "
                          << options_.evidence_path << "\n";
                return 1;
            }
            evidence << "probe_status=" << (success ? "success" : "timeout") << "\n"
                     << "domain_id=" << options_.domain_id << "\n"
                     << "interface=" << options_.interface_name << "\n"
                     << "topic=" << kTopic << "\n"
                     << "publishes_lowcmd=false\n"
                     << "minimum_valid_samples=" << options_.minimum_samples << "\n"
                     << "valid_samples=" << valid_samples << "\n"
                     << "first_tick=" << first_tick << "\n"
                     << "last_tick=" << last_tick << "\n"
                     << "timeout_s=" << std::setprecision(17)
                     << options_.timeout_s << "\n";
        }

        if (!success)
        {
            std::cerr << "DDS_PROBE_TIMEOUT valid_samples=" << valid_samples
                      << " required=" << options_.minimum_samples << "\n";
            return 1;
        }
        std::cout << "DDS_PROBE_SUCCESS valid_samples=" << valid_samples
                  << " first_tick=" << first_tick
                  << " last_tick=" << last_tick << "\n";
        return 0;
    }

private:
    void OnLowState(const void *message)
    {
        if (message == nullptr)
            return;
        const auto *state = static_cast<const LowState *>(message);
        if (state->motor_state().size() != 20)
            return;
        for (float value : state->imu_state().quaternion())
        {
            if (!std::isfinite(value))
                return;
        }

        std::lock_guard<std::mutex> lock(mutex_);
        const std::uint32_t tick = state->tick();
        if (have_tick_ && tick <= last_tick_)
            return;
        if (!have_tick_)
        {
            first_tick_ = tick;
            have_tick_ = true;
        }
        last_tick_ = tick;
        ++valid_samples_;
        condition_.notify_one();
    }

    const Options &options_;
    std::mutex mutex_;
    std::condition_variable condition_;
    std::size_t valid_samples_ = 0;
    std::uint32_t first_tick_ = 0;
    std::uint32_t last_tick_ = 0;
    bool have_tick_ = false;
    std::shared_ptr<unitree::robot::ChannelSubscriber<LowState>> subscriber_;
};

} // namespace

int main(int argc, char **argv)
{
    Options options;
    const bool help_requested = argc == 2 &&
        (std::string(argv[1]) == "--help" || std::string(argv[1]) == "-h");
    if (!ParseOptions(argc, argv, &options))
    {
        PrintUsage(argv[0]);
        return help_requested ? 0 : 2;
    }

    try
    {
        return LowStateProbe(options).Run();
    }
    catch (const std::exception &error)
    {
        std::cerr << "DDS_PROBE_INIT_FAILURE " << error.what() << "\n";
        return 1;
    }
}
