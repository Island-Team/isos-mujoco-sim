#pragma once

#include <atomic>
#include <filesystem>
#include <thread>

#include "strict_ledger.h"

namespace eos_mujoco {
class SimEngine;

// One framed request per connection. The engine is shared with the benchmark
// endpoint, so observations and commands refer to the same live simulation.
class V2Server {
 public:
  V2Server(const std::filesystem::path& socket, SimEngine& engine, bool managed_strict_socket);
  ~V2Server();
  V2Server(const V2Server&) = delete;
  V2Server& operator=(const V2Server&) = delete;

 private:
  void Run();
  void HandleStrict(int fd);
  StrictLedger ledger_;
  bool managed_strict_socket_ = false;
  std::filesystem::path socket_;
  SimEngine& engine_;
  int listener_ = -1;
  std::atomic_bool stopping_{false};
  std::thread worker_;
};
}  // namespace eos_mujoco
