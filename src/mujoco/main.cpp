#include <cstdint>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>

#include "engine.h"

int main(int argc, char** argv) {
  try {
    std::string scene;
    std::uint64_t seed = 0;
    int steps = 0;
    for (int i = 1; i < argc; ++i) {
      const std::string key = argv[i];
      if (key == "--help") {
        std::cout << "Usage: mujoco-core --scene PATH [--seed N] [--steps N]\n";
        return 0;
      }
      if (i + 1 >= argc) throw std::invalid_argument("missing value for " + key);
      const std::string value = argv[++i];
      if (key == "--scene")
        scene = value;
      else if (key == "--seed")
        seed = std::stoull(value);
      else if (key == "--steps")
        steps = std::stoi(value);
      else
        throw std::invalid_argument("unknown option: " + key);
    }
    if (scene.empty() || steps < 0) throw std::invalid_argument("scene required; steps must be nonnegative");
    eos_mujoco::SimEngine engine(scene);
    std::string error;
    if (!engine.Load(&error) || !engine.Reset(seed, &error)) throw std::runtime_error(error);
    engine.Step(steps);
    const auto snapshot = engine.GetSnapshot();
    std::cout << "profile=" << engine.SceneProfile() << " seed=" << seed
              << " steps=" << steps << " sequence=" << snapshot.sequence
              << " simulation_time_s=" << snapshot.simulation_time_s << '\n';
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "mujoco-core: " << error.what() << '\n';
    return 1;
  }
}
