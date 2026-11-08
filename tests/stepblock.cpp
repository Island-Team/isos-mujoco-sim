#include <dlfcn.h>
#include <fcntl.h>
#include <mujoco/mujoco.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <thread>

// Test-only preload: hold the ticker's first physics step while it owns the
// engine mutex. A stop must return unknown on its own deadline, then retain
// the movement fence after this call eventually resumes.
extern "C" void mj_step(const mjModel* model, mjData* data) {
  using Function = void (*)(const mjModel*, mjData*);
  static auto original = reinterpret_cast<Function>(dlsym(RTLD_NEXT, "mj_step"));
  static std::atomic_bool blocked{false};
  const char* arm = std::getenv("R06_STEP_BLOCK_ARM_FILE");
  if (arm && ::access(arm, F_OK) == 0 && !blocked.exchange(true)) {
    if (const char* marker = std::getenv("R06_STEP_BLOCK_MARKER")) {
      const int fd = ::open(marker, O_CREAT | O_WRONLY | O_TRUNC, 0600);
      if (fd >= 0) {
        ::write(fd, "blocked", 7);
        ::close(fd);
      }
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(2400));
  }
  original(model, data);
}
