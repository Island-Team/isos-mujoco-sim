add_library(mujoco_core STATIC engine.cpp gui.cpp)
add_dependencies(mujoco_core scene_devices_generated)
target_include_directories(mujoco_core PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}" PRIVATE "${GENERATED_DIR}")
target_link_libraries(mujoco_core PUBLIC Threads::Threads JPEG::JPEG X11::X11 ${EGL_LIBRARY} mujoco)
add_executable(mujoco-core main.cpp)
target_link_libraries(mujoco-core PRIVATE mujoco_core)
set_target_properties(mujoco-core PROPERTIES BUILD_RPATH "${MUJOCO_ROOT}/lib"
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
