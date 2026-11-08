#include <atomic>
#include <csignal>
#include <cstdlib>
#include <exception>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

#include "service.h"

namespace {
std::atomic_bool stop{false};
void StopSignal(int) { stop.store(true); }
}  // namespace

int main(int argc, char** argv) {
  try {
    std::filesystem::path socket;
    std::filesystem::path benchmark_socket;
    std::filesystem::path v2_socket;
    std::filesystem::path scene;
    bool manual_step = false;
    bool managed_strict_socket = false;
    const char* gui_env = std::getenv("MUJOCO_GUI");
    bool gui = gui_env && (std::string(gui_env) == "1" || std::string(gui_env) == "true");
    for (int i = 1; i < argc; ++i) {
      const std::string key = argv[i];
      if (key == "--manual-step") {
        manual_step = true;
        continue;
      }
      if (key == "--managed-strict-socket") {
        managed_strict_socket = true;
        continue;
      }
      if (key == "--gui") {
        gui = true;
        continue;
      }
      if (key == "--help") {
        std::cout << "Usage: eos-mujoco-sim --socket PATH --benchmark-socket PATH "
                     "--scene PATH [--v2-socket PATH] [--managed-strict-socket] "
                     "[--manual-step] [--gui]\n";
        return 0;
      }
      if (i + 1 >= argc) throw std::invalid_argument("missing value for " + key);
      const std::string value = argv[++i];
      if (key == "--socket")
        socket = value;
      else if (key == "--benchmark-socket")
        benchmark_socket = value;
      else if (key == "--v2-socket")
        v2_socket = value;
      else if (key == "--scene")
        scene = value;
      else
        throw std::invalid_argument("unknown option: " + key);
    }
    if (managed_strict_socket && v2_socket.empty())
      throw std::invalid_argument("strict_v2_socket_required");
    if (managed_strict_socket && !socket.empty())
      throw std::invalid_argument("strict_legacy_socket_forbidden");
    if (managed_strict_socket && !benchmark_socket.empty())
      throw std::invalid_argument("strict_benchmark_socket_forbidden");
    if ((!managed_strict_socket && (!socket.is_absolute() || !benchmark_socket.is_absolute())) ||
        !scene.is_absolute())
      throw std::invalid_argument(
          "--socket, --benchmark-socket, and --scene must be absolute paths");
    if (!managed_strict_socket && socket == benchmark_socket)
      throw std::invalid_argument("simulator and benchmark sockets must differ");
    if (!v2_socket.empty() &&
        (!v2_socket.is_absolute() || v2_socket == socket || v2_socket == benchmark_socket))
      throw std::invalid_argument("--v2-socket must be an absolute, distinct path");
    if (!std::filesystem::is_regular_file(scene))
      throw std::invalid_argument("scene does not exist: " + scene.string());
    std::signal(SIGINT, StopSignal);
    std::signal(SIGTERM, StopSignal);
    eos_mujoco::Serve(socket, benchmark_socket, v2_socket, scene, stop, manual_step, gui,
                      managed_strict_socket);
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "eos-mujoco-sim: " << error.what() << '\n';
    return 1;
  }
}
