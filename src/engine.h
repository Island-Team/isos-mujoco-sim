#pragma once

#include <array>
#include <atomic>
#include <cstdint>
#include <mutex>
#include <string>
#include <vector>

struct mjModel_;
struct mjData_;
struct mjvScene_;
struct mjrContext_;

namespace eos_mujoco {

struct Command {
  enum class Type {
    ArmMoveL,
    ArmMoveJ,
    ArmStop,
    BaseDrive,
    BaseNavigateRelative,
    BaseStop,
    GripperMove,
    GripperStop,
    Halt
  } type;
  std::array<double, 7> values{};  // XYZ+quaternion, six joints, or base x/y/yaw.
  bool close = false;
  double force_n = 0;
};
struct CommandResult {
  bool accepted = false;
  std::string error_code;
};
struct Snapshot {
  std::array<double, 6> joint_positions_rad{}, joint_velocities_rad_s{};
  std::array<double, 3> ee_position{}, ee_linear_velocity{};
  std::array<double, 4> ee_orientation_xyzw{0, 0, 0, 1};
  std::array<double, 3> base_pose{}, base_velocity{}, object_position{}, pinch_position{};
  std::array<std::array<double, 2>, 2> obstacle_positions{};
  bool arm_contact = false;
  std::string object_held_id;
  double gripper_force_n = 0, gripper_position_pct = 0;
  double simulation_time_s = 0;
  std::uint64_t sequence = 0;
};
struct CameraFrame {
  int width = 0, height = 0;
  std::int64_t timestamp_ns = 0;
  std::vector<std::uint8_t> jpeg;
  std::uint64_t sequence = 0;
};
struct Score {
  bool navigation = false, grasp = false, placement = false;
  int collisions = 0;
  double elapsed_s = 0;
};

struct RenderState;

class SimEngine {
 public:
  explicit SimEngine(std::string scene_path);
  ~SimEngine();
  SimEngine(const SimEngine&) = delete;
  SimEngine& operator=(const SimEngine&) = delete;
  bool Load(std::string* error);
  bool Reset(std::uint64_t seed, std::string* error);
  CommandResult Execute(const Command& command);
  Snapshot GetSnapshot() const;
  CameraFrame RenderCamera();
  Score GetScore() const;
  void Step(int steps);
  bool MotionActive() const { return active_motion_.load(); }
  std::string SceneProfile() const;
  bool JointTargetsInRange(const std::array<double, 6>& targets) const;

 private:
  enum class BenchmarkProfile { PickPlace, Navigation };
  void StepLocked(int steps);
  Snapshot SnapshotLocked() const;
  bool ResolveIds(std::string* error);
  std::string scene_path_;
  BenchmarkProfile profile_ = BenchmarkProfile::PickPlace;
  mutable std::mutex mutex_;
  mjModel_* model_ = nullptr;
  mjData_* data_ = nullptr;
  RenderState* render_state_ = nullptr;
  bool render_failed_ = false;
  int joint_ids_[6]{}, actuator_ids_[6]{};
  int base_joint_ids_[3]{}, base_actuator_ids_[3]{};
  int gripper_actuator_id_ = -1, grip_site_id_ = -1, object_body_id_ = -1;
  int ee_site_id_ = -1, camera_id_ = -1, object_free_joint_id_ = -1;
  int left_pad_id_ = -1, right_pad_id_ = -1;
  int goal_site_id_ = -1;
  std::uint64_t sequence_ = 0, interruption_epoch_ = 0;
  std::atomic_bool active_motion_{false};
  double base_drive_[3]{}, base_hold_[3]{}, target_joint_[6]{}, gripper_target_ = 0;
  double base_drive_until_s_ = 0;  // 0 keeps legacy gRPC drive behavior.
  bool base_drive_active_ = false, halted_ = false, collision_active_ = false;
  int collisions_ = 0;
  double lifted_contact_duration_s_ = 0;
};
}  // namespace eos_mujoco
