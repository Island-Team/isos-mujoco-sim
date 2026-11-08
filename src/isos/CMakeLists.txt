add_executable(eos-mujoco-sim main.cpp service.cpp adapter.cpp ${GENERATED_SOURCES})
add_dependencies(eos-mujoco-sim proto_generated)
add_dependencies(eos-mujoco-sim scene_devices_generated)
target_include_directories(eos-mujoco-sim PRIVATE "${GENERATED_DIR}" "${CMAKE_CURRENT_SOURCE_DIR}")
target_link_libraries(eos-mujoco-sim PRIVATE mujoco_core gRPC::grpc++ protobuf::libprotobuf)
set_target_properties(eos-mujoco-sim PROPERTIES BUILD_RPATH "${MUJOCO_ROOT}/lib"
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
install(TARGETS eos-mujoco-sim RUNTIME DESTINATION bin)
