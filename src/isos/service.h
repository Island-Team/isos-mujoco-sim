#pragma once

#include <atomic>
#include <filesystem>
#include <string>

namespace eos_mujoco {

// Runs both the EOS-compatible device endpoint and the private benchmark
// endpoint. Both are Unix domain sockets and are removed on shutdown.
void Serve(const std::filesystem::path& simulator_socket,
           const std::filesystem::path& benchmark_socket, const std::filesystem::path& v2_socket,
           const std::filesystem::path& scene, const std::atomic_bool& stop, bool manual_step,
           bool gui, bool managed_strict_socket);

}  // namespace eos_mujoco
