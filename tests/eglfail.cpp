#include <EGL/egl.h>

// Test-only preload: force the renderer's display acquisition to fail.
extern "C" __eglMustCastToProperFunctionPointerType eglGetProcAddress(const char*) {
  return nullptr;
}

extern "C" EGLDisplay eglGetDisplay(EGLNativeDisplayType) { return EGL_NO_DISPLAY; }
