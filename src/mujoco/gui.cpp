#include "gui.h"

#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <jpeglib.h>

#include <chrono>
#include <cstdlib>
#include <stdexcept>
#include <thread>
#include <vector>

#include "engine.h"

namespace eos_mujoco {
namespace {
unsigned long Channel(unsigned char value, unsigned long mask) {
  if (!mask) return 0;
  const unsigned shift = __builtin_ctzl(mask);
  const unsigned long scale = mask >> shift;
  return ((static_cast<unsigned long>(value) * scale + 127) / 255 << shift) & mask;
}
bool DecodeJpeg(const CameraFrame& frame, std::vector<unsigned char>* rgb) {
  if (frame.jpeg.empty()) return false;
  jpeg_decompress_struct jpeg{};
  jpeg_error_mgr error{};
  jpeg.err = jpeg_std_error(&error);
  jpeg_create_decompress(&jpeg);
  jpeg_mem_src(&jpeg, frame.jpeg.data(), frame.jpeg.size());
  if (jpeg_read_header(&jpeg, TRUE) != JPEG_HEADER_OK) {
    jpeg_destroy_decompress(&jpeg);
    return false;
  }
  jpeg_start_decompress(&jpeg);
  if (jpeg.output_width != 640 || jpeg.output_height != 480 || jpeg.output_components != 3) {
    jpeg_destroy_decompress(&jpeg);
    return false;
  }
  rgb->resize(640 * 480 * 3);
  while (jpeg.output_scanline < jpeg.output_height) {
    JSAMPROW row = rgb->data() + jpeg.output_scanline * 640 * 3;
    jpeg_read_scanlines(&jpeg, &row, 1);
  }
  jpeg_finish_decompress(&jpeg);
  jpeg_destroy_decompress(&jpeg);
  return true;
}
}  // namespace

GuiWindow::GuiWindow(SimEngine& engine) : engine_(engine) {
  display_ = XOpenDisplay(nullptr);
  if (!display_) throw std::runtime_error("--gui requires an available X11 display");
  const int screen = DefaultScreen(display_);
  window_ = XCreateSimpleWindow(display_, RootWindow(display_, screen), 100, 100, 640, 480, 0,
                                BlackPixel(display_, screen), BlackPixel(display_, screen));
  XStoreName(display_, window_, "IsOS MuJoCo — live simulation");
  XSelectInput(display_, window_, ExposureMask | StructureNotifyMask);
  XMapWindow(display_, window_);
  XFlush(display_);
  worker_ = std::thread([this] { Run(); });
}
GuiWindow::~GuiWindow() {
  stopping_.store(true);
  if (worker_.joinable()) worker_.join();
  if (display_) {
    XDestroyWindow(display_, window_);
    XCloseDisplay(display_);
  }
}
void GuiWindow::Run() {
  Visual* visual = DefaultVisual(display_, DefaultScreen(display_));
  const int depth = DefaultDepth(display_, DefaultScreen(display_));
  GC context = XCreateGC(display_, window_, 0, nullptr);
  while (!stopping_.load()) {
    while (XPending(display_)) {
      XEvent event;
      XNextEvent(display_, &event);
      if (event.type == DestroyNotify) stopping_.store(true);
    }
    const auto frame = engine_.RenderCamera();
    std::vector<unsigned char> rgb;
    if (DecodeJpeg(frame, &rgb)) {
      auto* pixels = static_cast<char*>(std::calloc(640 * 480, 4));
      if (!pixels) break;
      XImage* image = XCreateImage(display_, visual, depth, ZPixmap, 0, pixels, 640, 480, 32, 0);
      if (!image) {
        std::free(pixels);
        break;
      }
      for (int y = 0; y < 480; ++y) {
        for (int x = 0; x < 640; ++x) {
          const size_t offset = (y * 640 + x) * 3;
          const unsigned long color = Channel(rgb[offset], visual->red_mask) |
                                      Channel(rgb[offset + 1], visual->green_mask) |
                                      Channel(rgb[offset + 2], visual->blue_mask);
          XPutPixel(image, x, y, color);
        }
      }
      XPutImage(display_, window_, context, image, 0, 0, 0, 0, 640, 480);
      XFlush(display_);
      XDestroyImage(image);
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }
  XFreeGC(display_, context);
}
}  // namespace eos_mujoco
