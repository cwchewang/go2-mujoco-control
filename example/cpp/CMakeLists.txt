cmake_minimum_required(VERSION 3.16)
project(stand_go2)
enable_testing()

# Release is the default; explicit Debug and multi-config builds remain usable.
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

list(APPEND CMAKE_PREFIX_PATH "/opt/unitree_robotics/lib/cmake")
find_package(unitree_sdk2 REQUIRED)
find_package(Eigen3 REQUIRED)

set(GO2_CPP_INCLUDE_DIRS
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/apps
    ${CMAKE_CURRENT_SOURCE_DIR}/trot
    ${CMAKE_CURRENT_SOURCE_DIR}/gait
    ${CMAKE_CURRENT_SOURCE_DIR}/kinematics
    ${CMAKE_CURRENT_SOURCE_DIR}/contact
    ${CMAKE_CURRENT_SOURCE_DIR}/wbc
    ${CMAKE_CURRENT_SOURCE_DIR}/util
    ${CMAKE_CURRENT_SOURCE_DIR}/leg_lift
    ${CMAKE_CURRENT_SOURCE_DIR}/terrain
)
include_directories(${GO2_CPP_INCLUDE_DIRS})

set(GO2_MUJOCO_ROOT
    "${CMAKE_CURRENT_SOURCE_DIR}/../../simulate/mujoco" CACHE PATH
    "MuJoCo SDK/runtime root used for the controller build")
set(_go2_mujoco_lib "${GO2_MUJOCO_ROOT}/lib/libmujoco.so")
set(_go2_mujoco_inc "${GO2_MUJOCO_ROOT}/include")
set(_go2_model_path
    "${CMAKE_CURRENT_SOURCE_DIR}/../../unitree_robots/go2/go2.xml")

function(go2_link_mujoco target)
    target_include_directories(${target} PRIVATE "${_go2_mujoco_inc}")
    target_link_libraries(${target} "${_go2_mujoco_lib}")
    target_compile_definitions(${target} PRIVATE GO2_MODEL_PATH="${_go2_model_path}")
endfunction()

# Register a test beside its target: adding a test cannot silently omit CTest.
function(go2_test name)
    add_executable(${name} tests/${name}.cpp ${ARGN})
    add_test(NAME ${name} COMMAND ${name})
endfunction()

foreach(name IN ITEMS stand_go2 hold_pose_go2 track_lowcmd_lowstate_go2
                      dds_lowstate_probe single_leg_lift_go2)
    add_executable(${name} apps/${name}.cpp)
    target_link_libraries(${name} unitree_sdk2)
endforeach()
# dds_lowstate_probe is subscription-only; it creates no LowCmd publisher.

add_executable(real_leg_lift_go2
    leg_lift/real_leg_lift_go2.cpp
    leg_lift/leg_lift_cli.cpp
    leg_lift/leg_lift_lifecycle.cpp
    leg_lift/leg_lift_world.cpp
    leg_lift/leg_lift_diagnostics.cpp
    leg_lift/leg_lift_control.cpp)
target_link_libraries(real_leg_lift_go2 unitree_sdk2)

set(GO2_TROT_RUNTIME_SOURCES
    trot/trot_task.cpp
    trot/trot_experiment_lifecycle.cpp
    trot/trot_experiment_gait.cpp
    trot/trot_experiment_wbc.cpp
    trot/trot_experiment_diagnostics.cpp
    trot/trot_experiment_control.cpp)
add_executable(real_trot_go2
    trot/real_trot_go2.cpp trot/trot_cli.cpp ${GO2_TROT_RUNTIME_SOURCES})
target_link_libraries(real_trot_go2 unitree_sdk2 Eigen3::Eigen)

add_test(NAME test_dds_runtime
    COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/tests/test_dds_runtime.sh
                 ${CMAKE_CURRENT_SOURCE_DIR}/../..)

foreach(name IN ITEMS
        test_go2_inverse_kinematics test_raibert_footstep_planner
        test_cartesian_world_trot test_motion_frame_utils test_velocity_filter
        test_velocity_command test_contact_state_filter test_contact_fusion_fault_harness
        test_dynamic_acceleration_target test_motion_event_response test_wbc_runtime_gate
        test_lockstep_writer_gate test_lockstep_motion_clock test_centroidal_wbc
        test_clean_baseline)
    go2_test(${name})
endforeach()

foreach(name IN ITEMS
        test_raibert_trot_kernel test_contact_wrench_allocator test_go2_leg_jacobian
        test_contact_wrench_constraints test_contact_torque_mapping
        test_projected_contact_wrench_allocator test_contact_wrench_lexicographic_allocator
        test_preview_footstep_horizon test_dense_qp test_contact_wrench_qp test_srbd_mpc)
    go2_test(${name})
    target_link_libraries(${name} Eigen3::Eigen)
endforeach()

go2_test(test_trot_task trot/trot_task.cpp)
go2_test(test_lean_route_guard trot/trot_cli.cpp trot/trot_task.cpp)
target_link_libraries(test_lean_route_guard unitree_sdk2 Eigen3::Eigen)
go2_test(test_terrain_interfaces)
target_link_libraries(test_terrain_interfaces unitree_sdk2)

# Production call-chain test with test-only publish suppression/observability.
go2_test(test_lockstep_motion_clock_integration ${GO2_TROT_RUNTIME_SOURCES})
target_compile_definitions(test_lockstep_motion_clock_integration PRIVATE GO2_TROT_TESTING=1)
target_link_libraries(test_lockstep_motion_clock_integration unitree_sdk2 Eigen3::Eigen)

if(EXISTS "${_go2_mujoco_lib}")
    go2_test(test_go2_forward_kinematics)
    go2_link_mujoco(test_go2_forward_kinematics)
    foreach(name IN ITEMS test_go2_rigid_body test_inverse_dynamics_wbc)
        go2_test(${name})
        go2_link_mujoco(${name})
        target_link_libraries(${name} Eigen3::Eigen)
    endforeach()
    foreach(name IN ITEMS real_trot_go2 test_lockstep_motion_clock_integration)
        go2_link_mujoco(${name})
    endforeach()
    foreach(name IN ITEMS real_trot_go2 test_lockstep_motion_clock_integration
                          test_go2_rigid_body test_inverse_dynamics_wbc)
        set_target_properties(${name} PROPERTIES BUILD_RPATH "${GO2_MUJOCO_ROOT}/lib")
    endforeach()
endif()

add_executable(analyze_contact_torque_replay tools/analysis/analyze_contact_torque_replay.cpp)
target_include_directories(analyze_contact_torque_replay PRIVATE ${GO2_CPP_INCLUDE_DIRS})
target_link_libraries(analyze_contact_torque_replay Eigen3::Eigen)
