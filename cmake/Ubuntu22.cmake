# This opt-in profile never changes the default native build baseline.
if(CMAKE_CROSSCOMPILING)
  message(FATAL_ERROR "ubuntu22 does not support cross-compilation; use a native Ubuntu 22.04 toolchain")
endif()
if(NOT CMAKE_HOST_SYSTEM_NAME STREQUAL "Linux")
  message(FATAL_ERROR "ubuntu22 requires a native Ubuntu 22.04 build host")
endif()
file(STRINGS "/etc/os-release" ubuntu_id REGEX "^ID=")
file(STRINGS "/etc/os-release" ubuntu_version REGEX "^VERSION_ID=")
if(NOT ubuntu_id MATCHES "^ID=\"?ubuntu\"?$" OR
   NOT ubuntu_version MATCHES "^VERSION_ID=\"?22\\.04\"?$")
  message(FATAL_ERROR "ubuntu22 requires Ubuntu 22.04; use a 22.04 host or container")
endif()
execute_process(COMMAND getconf GNU_LIBC_VERSION
  OUTPUT_VARIABLE ubuntu_glibc OUTPUT_STRIP_TRAILING_WHITESPACE
  RESULT_VARIABLE ubuntu_glibc_status)
if(NOT ubuntu_glibc_status EQUAL 0 OR NOT ubuntu_glibc STREQUAL "glibc 2.35")
  message(FATAL_ERROR "ubuntu22 requires glibc 2.35; found ${ubuntu_glibc}")
endif()
