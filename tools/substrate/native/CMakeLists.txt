cmake_minimum_required(VERSION 3.20)
project(go2_substrate_admission LANGUAGES C CXX)
if(NOT DEFINED MJPC_SOURCE_DIR)
  message(FATAL_ERROR "Set MJPC_SOURCE_DIR to the pinned source checkout")
endif()
find_package(Git REQUIRED)
execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${MJPC_SOURCE_DIR}" rev-parse HEAD
  OUTPUT_VARIABLE MJPC_COMMIT OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
if(NOT MJPC_COMMIT STREQUAL "e00c47a5adb9856af2e0f24231bb3a60d5be23c4")
  message(FATAL_ERROR "MJPC source commit does not match sources.lock.json")
endif()
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(MUJOCO_ROOT "$ENV{HOME}/.mujoco/mujoco-3.3.6" CACHE PATH "MuJoCo 3.3.6 distribution")
find_path(MUJOCO_INCLUDE_DIR mujoco/mujoco.h PATHS "${MUJOCO_ROOT}/include" NO_DEFAULT_PATH REQUIRED)
find_library(MUJOCO_LIBRARY mujoco PATHS "${MUJOCO_ROOT}/lib" NO_DEFAULT_PATH REQUIRED)
find_package(Threads REQUIRED)
include(FetchContent)
set(ABSL_PROPAGATE_CXX_STD ON CACHE BOOL "" FORCE)
set(ABSL_BUILD_TESTING OFF CACHE BOOL "" FORCE)
FetchContent_Declare(abseil
  GIT_REPOSITORY https://github.com/abseil/abseil-cpp.git
  GIT_TAG fb3621f4f897824c0dbe0615fa94543df6192f30)
FetchContent_MakeAvailable(abseil)
execute_process(COMMAND "${GIT_EXECUTABLE}" -C "${abseil_SOURCE_DIR}" rev-parse HEAD
  OUTPUT_VARIABLE ABSL_COMMIT OUTPUT_STRIP_TRAILING_WHITESPACE COMMAND_ERROR_IS_FATAL ANY)
if(NOT ABSL_COMMIT STREQUAL "fb3621f4f897824c0dbe0615fa94543df6192f30")
  message(FATAL_ERROR "Abseil source commit differs from the pinned dependency")
endif()
# Build only the unchanged upstream optimizer. Built-in task assets, GUI,
# estimators, and unrelated robot repositories are not dependencies of this tool.
set(MJPC_FILES task.cc norm.cc utilities.cc trajectory.cc threadpool.cc
  states/state.cc planners/planner.cc planners/model_derivatives.cc
  planners/cost_derivatives.cc planners/ilqg/backward_pass.cc
  planners/ilqg/policy.cc planners/ilqg/planner.cc)
list(TRANSFORM MJPC_FILES PREPEND "${MJPC_SOURCE_DIR}/mjpc/")
add_library(go2_mjpc_core STATIC ${MJPC_FILES})
target_include_directories(go2_mjpc_core PUBLIC "${MJPC_SOURCE_DIR}" "${MUJOCO_INCLUDE_DIR}")
target_link_libraries(go2_mjpc_core PUBLIC "${MUJOCO_LIBRARY}" Threads::Threads
  absl::base absl::any_invocable absl::check absl::flat_hash_map absl::log
  absl::random_random absl::span)
add_executable(go2_mjpc_admit admit.cc)
target_link_libraries(go2_mjpc_admit PRIVATE go2_mjpc_core)

# The upstream Agent registry constructs every planner and estimator even when
# this admission selects only the XML-declared iLQG planner. Build that source
# subset directly so the executable does not inherit the interactive app's
# GLFW/window-system dependency.
set(MJPC_AGENT_FILES
  agent.cc
  planners/include.cc
  planners/cross_entropy/planner.cc
  planners/robust/robust_planner.cc
  planners/sample_gradient/planner.cc
  planners/sampling/planner.cc
  planners/sampling/policy.cc
  planners/gradient/gradient.cc
  planners/gradient/planner.cc
  planners/gradient/policy.cc
  planners/gradient/spline_mapping.cc
  planners/ilqs/planner.cc
  planners/shooting/planner.cc
  planners/shooting/policy.cc
  planners/shooting/gauss_newton.cc
  estimators/include.cc
  estimators/batch.cc
  estimators/kalman.cc
  estimators/unscented.cc
  direct/direct.cc
  direct/model_parameters.cc
  spline/spline.cc
  tasks/quadruped/quadruped.cc)
list(TRANSFORM MJPC_AGENT_FILES PREPEND "${MJPC_SOURCE_DIR}/mjpc/")
add_library(go2_mjpc_agent STATIC ${MJPC_AGENT_FILES})
target_include_directories(go2_mjpc_agent PUBLIC "${MJPC_SOURCE_DIR}" "${MUJOCO_INCLUDE_DIR}")
target_link_libraries(go2_mjpc_agent PUBLIC go2_mjpc_core Threads::Threads
  absl::any_invocable absl::check absl::flat_hash_map absl::log
  absl::random_random absl::span)

add_executable(go2_mjpc_comparator_probe comparator_probe.cc)
target_link_libraries(go2_mjpc_comparator_probe PRIVATE go2_mjpc_agent)
target_compile_definitions(go2_mjpc_comparator_probe PRIVATE
  GO2_MJPC_SOURCE_COMMIT="${MJPC_COMMIT}"
  GO2_CXX_COMPILER_ID="${CMAKE_CXX_COMPILER_ID}"
  GO2_CXX_COMPILER_VERSION="${CMAKE_CXX_COMPILER_VERSION}")

# QuadrupedFlat stores enum selections in doubles via reinterpretation. The
# selected upstream source crashes under GCC Release with strict aliasing on;
# keep this compatibility flag visible on every comparator compilation unit.
foreach(target go2_mjpc_core go2_mjpc_agent go2_mjpc_comparator_probe)
  target_compile_options(${target} PRIVATE -fno-strict-aliasing)
endforeach()
