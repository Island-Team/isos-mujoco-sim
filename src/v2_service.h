#pragma once

#include <atomic>
#include <condition_variable>
#include <deque>
#include <filesystem>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

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
  void Run(int listener, bool stop_lane);
  void Work(bool stop_lane);
  void HandleStrict(int fd, bool stop_lane);
  StrictLedger ledger_;
  std::mutex ledger_mutex_, queue_mutex_;
  std::condition_variable queue_ready_;
  std::deque<int> normal_queue_, stop_queue_;
  std::vector<std::thread> normal_workers_, stop_workers_;
  std::size_t normal_outstanding_ = 0, stop_outstanding_ = 0;
  std::atomic_int normal_ingress_{0};
  std::string generation_id_;
  std::string scene_profile_;
  bool managed_strict_socket_ = false;
  std::filesystem::path socket_, stop_socket_;
  SimEngine& engine_;
  int listener_ = -1, stop_listener_ = -1;
  std::atomic_bool stopping_{false};
  std::thread worker_, stop_worker_;
};
}  // namespace eos_mujoco
