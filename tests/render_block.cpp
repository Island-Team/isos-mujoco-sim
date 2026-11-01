#include <dlfcn.h>
#include <fcntl.h>
#include <mujoco/mujoco.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <thread>

// Test-only preload: the first render is managed-startup preflight; hold the
// next capture inside the graphics call while the companion stop is issued.
extern "C" void mjr_readPixels(unsigned char* rgb, float* depth, mjrRect viewport,
                               const mjrContext* context) {
  using Function = void (*)(unsigned char*, float*, mjrRect, const mjrContext*);
  static auto original = reinterpret_cast<Function>(dlsym(RTLD_NEXT, "mjr_readPixels"));
  static std::atomic_int calls{0};
  if (calls.fetch_add(1) == 1) {
    if (const char* marker = std::getenv("R06_RENDER_BLOCK_MARKER")) {
      const int fd = ::open(marker, O_CREAT | O_WRONLY | O_TRUNC, 0600);
      if (fd >= 0) {
        ::write(fd, "blocked", 7);
        ::close(fd);
      }
    }
    std::this_thread::sleep_for(std::chrono::seconds(2));
  }
  original(rgb, depth, viewport, context);
}
