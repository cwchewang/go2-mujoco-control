cmake_minimum_required(VERSION 3.16)
project(unitree_mujoco)

if (CMAKE_BUILD_TYPE MATCHES "Debug")
  message("Debug mode")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17 -g -O0 -fPIC")
else()
  message("Release mode")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++17 -O3 -DNDEBUG -fPIC")
endif()

list(APPEND CMAKE_PREFIX_PATH "/opt/unitree_robotics/lib/cmake")
find_package(unitree_sdk2 REQUIRED)
find_package(Boost REQUIRED COMPONENTS program_options)

set(MUJOCO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/mujoco" CACHE PATH
  "MuJoCo SDK/runtime root used for the exact-source simulator build")
if(NOT IS_DIRECTORY "${MUJOCO_ROOT}/include" OR
   NOT IS_DIRECTORY "${MUJOCO_ROOT}/lib")
  message(FATAL_ERROR
    "MUJOCO_ROOT must contain include/ and lib/: ${MUJOCO_ROOT}")
endif()

include_directories(
  /usr/local/include/iceoryx/v2.0.2
  "${MUJOCO_ROOT}/include"
  "${MUJOCO_ROOT}/simulate"
  src/lodepng
)
link_directories("${MUJOCO_ROOT}/lib")

file(GLOB SIM_SRC
  src/joystick/joystick.cc

  # exclude mujoco/simulate/main.cc
  "${MUJOCO_ROOT}/simulate/glfw_*.cc"
  "${MUJOCO_ROOT}/simulate/platform_*.cc"
  "${MUJOCO_ROOT}/simulate/simulate.cc"
  src/lodepng/lodepng.cpp
)

link_libraries(
  pthread
  mujoco
  glfw
  yaml-cpp
  unitree_sdk2
  boost_program_options
  fmt
)

add_executable(unitree_mujoco ${SIM_SRC} src/main.cc)

add_executable(jstest src/joystick/jstest.cc src/joystick/joystick.cc)

# ---- Order-103 lockstep verification tests ----
enable_testing()

add_executable(test_lockstep src/tests/test_lockstep.cpp)
target_include_directories(test_lockstep PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)
add_test(NAME test_lockstep COMMAND test_lockstep)

add_test(NAME test_lockstep_sim
  COMMAND bash ${CMAKE_CURRENT_SOURCE_DIR}/src/tests/run_lockstep_sim_tests.sh
          $<TARGET_FILE:unitree_mujoco>
          ${CMAKE_CURRENT_BINARY_DIR})
