#pragma once
#include <cstdlib>
#include <stdexcept>
#include <string>
namespace go2_substrate {
inline bool LogicalWarmstart() {
  const char* value = std::getenv("GO2_MJPC_WARMSTART_OWNER");
  if (!value || std::string(value) == "worker") return false;
  if (std::string(value) == "logical") return true;
  throw std::runtime_error("invalid warmstart owner");
}
}
