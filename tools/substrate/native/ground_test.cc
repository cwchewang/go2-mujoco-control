// Source-bound Ground miss regression. No physics integration is called.
#include <cmath>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <mujoco/mujoco.h>
#include "mjpc/utilities.h"

int main() {
  try {
    char error[1024] = {};
    mjVFS vfs;
    mj_defaultVFS(&vfs);
    const char xml[] =
        "<mujoco><worldbody>"
        "<geom type='plane' size='1 1 .1' group='0'/>"
        "<body pos='0 0 1'><freejoint/>"
        "<geom type='sphere' size='.1' group='1'/></body>"
        "</worldbody></mujoco>";
    if (mj_addBufferVFS(&vfs, "ground.xml", xml, sizeof(xml))) {
      throw std::runtime_error("fixture VFS creation failed");
    }
    std::unique_ptr<mjModel, decltype(&mj_deleteModel)> model(
        mj_loadXML("ground.xml", &vfs, error, sizeof(error)), mj_deleteModel);
    mj_deleteVFS(&vfs);
    if (!model) throw std::runtime_error(error);
    std::unique_ptr<mjData, decltype(&mj_deleteData)> data(
        mj_makeData(model.get()), mj_deleteData);
    mj_forward(model.get(), data.get());
    const mjtNum hit[3] = {0, 0, 1};
    if (std::abs(mjpc::Ground(model.get(), data.get(), hit)) > 1e-12 ||
        mjpc::CheckWarnings(data.get())) {
      throw std::runtime_error("valid ground query changed");
    }
    const mjtNum miss[3] = {0, 0, -1};
    const auto result = mjpc::Ground(model.get(), data.get(), miss);
    const int warnings = data->warning[mjWARN_BADQPOS].number;
    if (!std::isfinite(result) || warnings != 1 ||
        !mjpc::CheckWarnings(data.get()) || data->time != 0) {
      throw std::runtime_error("Ground miss was not rejected as warning");
    }
    std::cout << "{\"ground_miss_warning_count\":" << warnings
              << ",\"check_warnings_rejected\":true,"
                 "\"physics_integrations\":0,\"time_s\":0}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
