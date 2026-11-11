add_library(mujoco-eos-node SHARED node.cpp)
target_include_directories(mujoco-eos-node PRIVATE "${CMAKE_SOURCE_DIR}/include")
target_link_libraries(mujoco-eos-node PRIVATE protobuf::libprotobuf)
set_target_properties(mujoco-eos-node PROPERTIES
  PREFIX "lib" OUTPUT_NAME "mujoco-eos-node"
  LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
install(TARGETS mujoco-eos-node LIBRARY DESTINATION lib)
