#pragma once

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <deque>
#include <filesystem>
#include <future>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "engine.h"
#include "strict_ledger.h"

namespace eos_mujoco {

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
  void StopWork();
  void CancelActiveCapture();
  void HandleStrict(int fd, bool stop_lane, std::chrono::steady_clock::time_point ingress_deadline);
  struct QueuedConnection {
    int fd;
    std::chrono::steady_clock::time_point accepted_at;
    std::chrono::steady_clock::time_point ingress_deadline;
  };
  struct StopJob {
    std::uint64_t epoch;
    std::promise<StopProof> result;
  };
  StrictLedger ledger_;
  std::mutex ledger_mutex_, queue_mutex_, stop_jobs_mutex_, capture_fd_mutex_;
  std::timed_mutex publication_mutex_;
  int active_capture_fd_ = -1;
  std::condition_variable queue_ready_, stop_jobs_ready_;
  std::deque<std::shared_ptr<StopJob>> stop_jobs_;
  std::atomic_int pending_stop_jobs_{0};
  bool stop_inhibited_ = false;
  std::atomic_bool stop_unknown_latched_{false};
  std::deque<QueuedConnection> normal_queue_, stop_queue_;
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
  std::thread worker_, stop_worker_, stop_executor_;
};
}  // namespace eos_mujoco
