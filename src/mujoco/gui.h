#pragma once

#include <atomic>
#include <memory>
#include <thread>

struct _XDisplay;
namespace eos_mujoco {
class SimEngine;

// Shows frames captured from the same SimEngine used by both socket endpoints.
class GuiWindow {
 public:
  explicit GuiWindow(SimEngine& engine);
  ~GuiWindow();
  GuiWindow(const GuiWindow&) = delete;
  GuiWindow& operator=(const GuiWindow&) = delete;

 private:
  void Run();
  SimEngine& engine_;
  _XDisplay* display_ = nullptr;
  unsigned long window_ = 0;
  std::atomic_bool stopping_{false};
  std::thread worker_;
};
}  // namespace eos_mujoco
