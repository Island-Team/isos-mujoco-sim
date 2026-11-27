#include "engine.h"

#include <chrono>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <string>
#include <thread>

namespace {
bool Near(double a, double b, double eps) { return std::abs(a - b) < eps; }
int Fail(const char* message) {
  std::cerr << message << '\n';
  return 1;
}
}  // namespace

int main(int argc, char** argv) {
  if (argc != 2) return Fail("usage: engine-car-test CAR_SCENE");
  if (!std::filesystem::exists(std::filesystem::path(argv[1]).parent_path() / "meshes"))
    return Fail("car-scene meshes are not downloaded: run 'python tools/blendscene_assets.py download'");
  eos_mujoco::SimEngine engine(argv[1]);
  std::string error;
  if (!engine.Load(&error)) return Fail(error.c_str());
  if (engine.SceneProfile() != "eos_benchmark_car_navigation_v1")
    return Fail("car scene did not resolve the car navigation profile");
  if (!engine.Reset(42, &error)) return Fail(error.c_str());
  auto initial = engine.GetSnapshot();
  if (std::hypot(initial.base_pose[0] - 25.484, initial.base_pose[1] - 27.878) > 0.05)
    return Fail("reset did not restore the scene spawn pose");
  if (engine.GetScore().navigation || engine.GetScore().grasp || engine.GetScore().placement)
    return Fail("car scene started with a scored stage");
  engine.Reset(42, &error);
  auto replay = engine.GetSnapshot();
  for (int k = 0; k < 3; ++k)
    if (!Near(initial.base_pose[k], replay.base_pose[k], 1e-9))
      return Fail("same seed changed car pose");
  // Timed open-loop drive applies during Step, mirroring the wheel velocity contract.
  eos_mujoco::Command drive{};
  drive.type = eos_mujoco::Command::Type::BaseDrive;
  drive.values = {0.5, 0, 0, 2.0};
  if (!engine.Execute(drive).accepted) return Fail("car base drive rejected");
  engine.Step(1000);
  auto driven = engine.GetSnapshot();
  const double travelled = std::hypot(driven.base_pose[0] - initial.base_pose[0],
                                      driven.base_pose[1] - initial.base_pose[1]);
  if (travelled < 0.5 || travelled > 1.4) return Fail("timed drive did not move the car plausibly");
  if (std::abs(driven.joint_velocities_rad_s[0]) < 1.0)
    return Fail("wheel speeds missing from the snapshot");
  engine.Reset(42, &error);
  eos_mujoco::Command strafe{};
  strafe.type = eos_mujoco::Command::Type::BaseDrive;
  strafe.values = {0, 0.4, 0, 0};
  auto rejected = engine.Execute(strafe);
  if (rejected.accepted || rejected.error_code != "out_of_range")
    return Fail("differential drive accepted a strafe command");
  eos_mujoco::Command arm{};
  arm.type = eos_mujoco::Command::Type::ArmMoveJ;
  if (engine.Execute(arm).accepted) return Fail("car profile accepted an arm command");
  // Closed-loop relative navigation with managed-stop fencing.
  eos_mujoco::Command leg{};
  leg.type = eos_mujoco::Command::Type::BaseNavigateRelative;
  leg.values = {2, 0, 0, 0, 0, 0, 0};
  eos_mujoco::CommandResult motion;
  std::thread worker([&] { motion = engine.Execute(leg); });
  auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(1);
  while (!engine.MotionActive() && std::chrono::steady_clock::now() < deadline)
    std::this_thread::yield();
  if (!engine.MotionActive()) {
    worker.join();
    return Fail("car navigation did not enter active state");
  }
  eos_mujoco::Command stop{};
  stop.type = eos_mujoco::Command::Type::BaseStop;
  if (!engine.Execute(stop).accepted) return Fail("car base stop rejected");
  worker.join();
  if (motion.accepted || motion.error_code != "interrupted")
    return Fail("stop did not interrupt active car navigation");
  engine.Reset(42, &error);
  eos_mujoco::Command managed_drive = drive;
  if (!engine.Execute(managed_drive, 0).accepted) return Fail("managed car drive rejected");
  const auto proof = engine.ManagedStop();
  if (!proof.base_stopped || !proof.arm_stopped || !proof.gripper_stopped ||
      proof.stop_epoch != 1 || engine.StopEpoch() != 1)
    return Fail("car managed stop lacked committed holds and epoch");
  const auto after_stop = engine.GetSnapshot();
  auto delayed = engine.Execute(managed_drive, 0);
  if (delayed.accepted || delayed.error_code != "command_interrupted")
    return Fail("delayed car movement crossed the engine stop fence");
  engine.Step(10);
  auto settled = engine.GetSnapshot();
  if (std::hypot(settled.base_velocity[0], settled.base_velocity[1]) > 0.3)
    return Fail("car kept rolling after managed stop");
  if (engine.GetScore().collisions != 0)
    return Fail("normal driving was scored as collision");
  if (!engine.Execute(leg, 1).accepted) {
    std::cerr << "closed-loop leg error=" << motion.error_code << "\n";
    return Fail("current-epoch closed-loop car navigation rejected");
  }
  auto navigated = engine.GetSnapshot();
  const double leg_travelled =
      std::hypot(navigated.base_pose[0] - settled.base_pose[0], navigated.base_pose[1] - settled.base_pose[1]);
  if (leg_travelled < 1.2 || leg_travelled > 3.2)
    return Fail("closed-loop navigation did not cover the commanded leg");
  eos_mujoco::Command halt{};
  halt.type = eos_mujoco::Command::Type::Halt;
  if (!engine.Execute(halt).accepted || engine.Execute(drive).accepted)
    return Fail("halt did not disable car motion");
  if (!engine.Reset(42, &error) || !engine.Execute(drive).accepted)
    return Fail("reset did not clear halt");
  std::cout << "engine ok: car drive/stop/navigation invariants held, spawn=("
            << initial.base_pose[0] << "," << initial.base_pose[1] << ") travel=" << travelled
            << " leg=" << leg_travelled << "\n";
  return 0;
}
