#include <dlfcn.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <cstdlib>
#include <thread>

// Test-only preload: hold the first JPEG payload write after the server has
// checked its capture epoch. This exercises the publication-to-stop fence.
extern "C" ssize_t send(int fd, const void* buffer, size_t length, int flags) {
  using Function = ssize_t (*)(int, const void*, size_t, int);
  static auto original = reinterpret_cast<Function>(dlsym(RTLD_NEXT, "send"));
  static std::atomic_bool blocked{false};
  if (length > 2048 && !blocked.exchange(true)) {
    if (const char* marker = std::getenv("R06_SEND_BLOCK_MARKER")) {
      const int out = ::open(marker, O_CREAT | O_WRONLY | O_TRUNC, 0600);
      if (out >= 0) {
        ::write(out, "blocked", 7);
        ::close(out);
      }
    }
    if (const char* ms = std::getenv("R06_SEND_BLOCK_MS"))
      std::this_thread::sleep_for(std::chrono::milliseconds(std::atoi(ms)));
  }
  return original(fd, buffer, length, flags);
}
