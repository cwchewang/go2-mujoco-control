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
find_package(Python3 REQUIRED COMPONENTS Interpreter)
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
# Build pinned upstream sources through narrow, identity-checked generated overlays.
set(MJPC_PATCH_SCRIPT "${CMAKE_CURRENT_SOURCE_DIR}/patch_mjpc_utilities.py")
set(MJPC_PATCHED_UTILITIES
  "${CMAKE_CURRENT_BINARY_DIR}/generated/mjpc_utilities_hardened.cc")
set(MJPC_DERIVATIVE_PATCH_SCRIPT
  "${CMAKE_CURRENT_SOURCE_DIR}/patch_mjpc_model_derivatives.py")
set(MJPC_PATCHED_DERIVATIVES
  "${CMAKE_CURRENT_BINARY_DIR}/generated/model_derivatives_unique_indices.cc")
execute_process(
  COMMAND "${Python3_EXECUTABLE}" "${MJPC_PATCH_SCRIPT}"
          "${MJPC_SOURCE_DIR}/mjpc/utilities.cc" "${MJPC_PATCHED_UTILITIES}"
  COMMAND_ERROR_IS_FATAL ANY)
execute_process(
  COMMAND "${Python3_EXECUTABLE}" "${MJPC_DERIVATIVE_PATCH_SCRIPT}"
          "${MJPC_SOURCE_DIR}/mjpc/planners/model_derivatives.cc"
          "${MJPC_PATCHED_DERIVATIVES}"
  COMMAND_ERROR_IS_FATAL ANY)
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
  "${MJPC_PATCH_SCRIPT}" "${MJPC_SOURCE_DIR}/mjpc/utilities.cc"
  "${MJPC_DERIVATIVE_PATCH_SCRIPT}" "${MJPC_SOURCE_DIR}/mjpc/planners/model_derivatives.cc")
set(MJPC_FILES task.cc norm.cc trajectory.cc threadpool.cc
  states/state.cc planners/planner.cc
  planners/cost_derivatives.cc planners/ilqg/backward_pass.cc
  planners/ilqg/policy.cc planners/ilqg/planner.cc
  tasks/quadruped/quadruped.cc)
list(TRANSFORM MJPC_FILES PREPEND "${MJPC_SOURCE_DIR}/mjpc/")
list(APPEND MJPC_FILES "${MJPC_PATCHED_UTILITIES}" "${MJPC_PATCHED_DERIVATIVES}")
add_library(go2_mjpc_core STATIC ${MJPC_FILES})
target_include_directories(go2_mjpc_core PUBLIC "${MJPC_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}" "${MUJOCO_INCLUDE_DIR}")
add_executable(model_derivative_indices_test model_derivative_indices_test.cc)

option(GO2_MJPC_BUILD_FD_DIAGNOSTIC
  "Build matched original/fixed FD-traced diagnostic binaries" OFF)
if(GO2_MJPC_BUILD_FD_DIAGNOSTIC)
  set(MJPC_DIAGNOSTIC_PATCH_SCRIPT
    "${CMAKE_CURRENT_SOURCE_DIR}/patch_mjpc_model_derivatives_diagnostic.py")
  set(MJPC_FD_ORIGINAL_SOURCE
    "${CMAKE_CURRENT_BINARY_DIR}/generated/model_derivatives_fd_original.cc")
  set(MJPC_FD_FIXED_SOURCE
    "${CMAKE_CURRENT_BINARY_DIR}/generated/model_derivatives_fd_fixed.cc")
  execute_process(
    COMMAND "${Python3_EXECUTABLE}" "${MJPC_DIAGNOSTIC_PATCH_SCRIPT}"
            "${MJPC_SOURCE_DIR}/mjpc/planners/model_derivatives.cc"
            "${MJPC_FD_ORIGINAL_SOURCE}" "${MJPC_FD_FIXED_SOURCE}"
    COMMAND_ERROR_IS_FATAL ANY)
  set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
    "${MJPC_DIAGNOSTIC_PATCH_SCRIPT}"
    "${MJPC_SOURCE_DIR}/mjpc/planners/model_derivatives.cc")
  set(MJPC_DIAGNOSTIC_COMMON_FILES ${MJPC_FILES})
  list(REMOVE_ITEM MJPC_DIAGNOSTIC_COMMON_FILES "${MJPC_PATCHED_DERIVATIVES}")
  option(GO2_MJPC_LOGICAL_WARMSTART "Build matched logical warmstart ownership diagnostic" OFF)
  if(GO2_MJPC_LOGICAL_WARMSTART)
    execute_process(COMMAND "${Python3_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/patch_logical_warmstart.py"
      "${MJPC_SOURCE_DIR}" "${CMAKE_CURRENT_BINARY_DIR}/generated/logical"
      "${MJPC_FD_FIXED_SOURCE}" COMMAND_ERROR_IS_FATAL ANY)
    list(REMOVE_ITEM MJPC_DIAGNOSTIC_COMMON_FILES
      "${MJPC_SOURCE_DIR}/mjpc/trajectory.cc" "${MJPC_SOURCE_DIR}/mjpc/planners/ilqg/planner.cc")
    list(APPEND MJPC_DIAGNOSTIC_COMMON_FILES
      "${CMAKE_CURRENT_BINARY_DIR}/generated/logical/mjpc/trajectory.cc"
      "${CMAKE_CURRENT_BINARY_DIR}/generated/logical/mjpc/planners/ilqg/planner.cc")
    include_directories(BEFORE "${CMAKE_CURRENT_BINARY_DIR}/generated/logical")
  endif()
  foreach(variant IN ITEMS original fixed)
    if(variant STREQUAL "original")
      set(MJPC_FD_VARIANT_SOURCE "${MJPC_FD_ORIGINAL_SOURCE}")
    else()
      set(MJPC_FD_VARIANT_SOURCE "${MJPC_FD_FIXED_SOURCE}")
    endif()
    add_library(go2_mjpc_fd_${variant}_core STATIC
      ${MJPC_DIAGNOSTIC_COMMON_FILES} "${MJPC_FD_VARIANT_SOURCE}")
    target_include_directories(go2_mjpc_fd_${variant}_core PUBLIC
      "${MJPC_SOURCE_DIR}" "${CMAKE_CURRENT_SOURCE_DIR}" "${MUJOCO_INCLUDE_DIR}")
    target_link_libraries(go2_mjpc_fd_${variant}_core PUBLIC
      "${MUJOCO_LIBRARY}" Threads::Threads absl::base absl::any_invocable
      absl::check absl::flat_hash_map absl::log absl::random_random absl::span)
    target_compile_options(go2_mjpc_fd_${variant}_core PRIVATE -fno-strict-aliasing)
    add_executable(go2_mjpc_controller_fd_${variant} controller.cc diagnostic_budget.cc)
    target_link_libraries(go2_mjpc_controller_fd_${variant} PRIVATE
      go2_mjpc_fd_${variant}_core)
    target_link_options(go2_mjpc_controller_fd_${variant} PRIVATE
      "-Wl,--wrap=mj_step" "-Wl,--wrap=mjd_transitionFD")
  endforeach()
endif()
target_link_libraries(go2_mjpc_core PUBLIC "${MUJOCO_LIBRARY}" Threads::Threads
  absl::base absl::any_invocable absl::check absl::flat_hash_map absl::log
  absl::random_random absl::span)
# Pinned MJPC utilities use bit reinterpretation that is unsafe under
# strict-aliasing optimization. Release smokes are stable with this disabled.
target_compile_options(go2_mjpc_core PRIVATE -fno-strict-aliasing)
add_executable(go2_mjpc_admit admit.cc)
target_link_libraries(go2_mjpc_admit PRIVATE go2_mjpc_core)
add_executable(go2_mjpc_controller controller.cc diagnostic_budget.cc)
target_link_libraries(go2_mjpc_controller PRIVATE go2_mjpc_core)
target_link_options(go2_mjpc_controller PRIVATE "-Wl,--wrap=mj_step" "-Wl,--wrap=mjd_transitionFD")

enable_testing()
add_test(NAME model_derivative_indices_zero_integration
  COMMAND model_derivative_indices_test)
add_executable(go2_mjpc_ground_test ground_test.cc)
target_link_libraries(go2_mjpc_ground_test PRIVATE go2_mjpc_core)
add_test(NAME ground_miss_zero_integration COMMAND go2_mjpc_ground_test)

add_executable(go2_mjpc_fresh_plan_test fresh_plan_test.cc)
target_link_libraries(go2_mjpc_fresh_plan_test PRIVATE go2_mjpc_core)
add_test(NAME fresh_plan_zero_integration COMMAND go2_mjpc_fresh_plan_test)

add_executable(go2_mjpc_diagnostic_contract_test diagnostic_contract_test.cc)
target_link_libraries(go2_mjpc_diagnostic_contract_test PRIVATE go2_mjpc_core)
add_test(NAME diagnostic_mapping_zero_integration
  COMMAND go2_mjpc_diagnostic_contract_test
  "${MJPC_SOURCE_DIR}/mjpc/tasks/quadruped/task_flat.xml"
  "${CMAKE_CURRENT_SOURCE_DIR}/../../../unitree_robots/go2/phase2_flat.xml")
