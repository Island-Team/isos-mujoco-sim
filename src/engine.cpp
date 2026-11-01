#include "engine.h"

#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <jpeglib.h>
#include <mujoco/mujoco.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <thread>

namespace eos_mujoco {
namespace {
constexpr double kPi = 3.141592653589793;
constexpr std::array<const char*, 6> kJoints = {
    "shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
    "wrist_1_joint",      "wrist_2_joint",       "wrist_3_joint"};
constexpr std::array<const char*, 6> kActuators = {
    "shoulder_pan", "shoulder_lift", "elbow", "wrist_1", "wrist_2", "wrist_3"};
int Id(const mjModel* m, mjtObj kind, const char* name) {
  return mj_name2id(m, kind, name);
}
std::array<double, 4> Quaternion(const mjtNum* wxyz) {
  return {wxyz[1], wxyz[2], wxyz[3], wxyz[0]};
}
bool Finite(double v) { return std::isfinite(v); }
}  // namespace
struct RenderState {
  EGLDisplay display = EGL_NO_DISPLAY;
  EGLSurface surface = EGL_NO_SURFACE;
  EGLContext context = EGL_NO_CONTEXT;
  mjvScene scene{};
  mjrContext render{};
};
SimEngine::SimEngine(std::string path) : scene_path_(std::move(path)) {}

std::string SimEngine::SceneProfile() const {
  std::lock_guard lock(mutex_);
  return profile_ == BenchmarkProfile::Navigation
             ? "eos_benchmark_navigation_v1"
             : "eos_benchmark_pick_place_v1";
}

bool SimEngine::JointTargetsInRange(
    const std::array<double, 6>& targets) const {
  std::lock_guard lock(mutex_);
  if (!model_ || !data_) return false;
  for (int i = 0; i < 6; ++i) {
    const int joint = joint_ids_[i];
    if (joint < 0 || !std::isfinite(targets[i]) ||
        targets[i] < model_->jnt_range[2 * joint] ||
        targets[i] > model_->jnt_range[2 * joint + 1])
      return false;
  }
  return true;
}
SimEngine::~SimEngine() {
  std::lock_guard lock(mutex_);
  if (render_state_) {
    auto* r = render_state_;
    eglMakeCurrent(r->display, r->surface, r->surface, r->context);
    mjr_freeContext(&r->render);
    mjv_freeScene(&r->scene);
    eglMakeCurrent(r->display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
    eglDestroyContext(r->display, r->context);
    eglDestroySurface(r->display, r->surface);
    eglTerminate(r->display);
    delete r;
  }
  if (data_) {
    mj_deleteData(data_);
  }
  if (model_) {
    mj_deleteModel(model_);
  }
}
bool SimEngine::ResolveIds(std::string* error) {
  int recognized_profiles = 0;
  bool navigation = false;
  for (int i = 0; i < model_->nnumeric; ++i) {
    const char* name = mj_id2name(model_, mjOBJ_NUMERIC, i);
    if (!name || std::strncmp(name, "eos_benchmark_", 14) != 0) continue;
    if (std::strcmp(name, "eos_benchmark_pick_place_v1") == 0) {
      ++recognized_profiles;
    } else if (std::strcmp(name, "eos_benchmark_navigation_v1") == 0) {
      ++recognized_profiles;
      navigation = true;
    } else {
      if (error) *error = "unknown benchmark profile: " + std::string(name);
      return false;
    }
  }
  if (recognized_profiles != 1) {
    if (error)
      *error = "scene must declare exactly one supported benchmark profile";
    return false;
  }
  profile_ =
      navigation ? BenchmarkProfile::Navigation : BenchmarkProfile::PickPlace;
  goal_site_id_ = navigation ? Id(model_, mjOBJ_SITE, "navigation_goal") : -1;
  if (navigation && goal_site_id_ < 0) {
    if (error) *error = "navigation scene is missing navigation_goal site";
    return false;
  }
  for (int i = 0; i < 6; ++i) {
    joint_ids_[i] = Id(model_, mjOBJ_JOINT, kJoints[i]);
    actuator_ids_[i] = Id(model_, mjOBJ_ACTUATOR, kActuators[i]);
    if (joint_ids_[i] < 0 || actuator_ids_[i] < 0) {
      if (error) *error = "missing UR5e joint or actuator";
      return false;
    }
  }
  const char *bj[] = {"base_x", "base_y", "base_yaw"},
             *ba[] = {"base_x_motor", "base_y_motor", "base_yaw_motor"};
  for (int i = 0; i < 3; ++i) {
    base_joint_ids_[i] = Id(model_, mjOBJ_JOINT, bj[i]);
    base_actuator_ids_[i] = Id(model_, mjOBJ_ACTUATOR, ba[i]);
    if (base_joint_ids_[i] < 0 || base_actuator_ids_[i] < 0) {
      if (error) *error = "missing base joint or actuator";
      return false;
    }
  }
  gripper_actuator_id_ = Id(model_, mjOBJ_ACTUATOR, "gr_fingers_actuator");
  grip_site_id_ = Id(model_, mjOBJ_SITE, "gr_pinch");
  ee_site_id_ = Id(model_, mjOBJ_SITE, "attachment_site");
  object_body_id_ = Id(model_, mjOBJ_BODY, "benchmark_object");
  object_free_joint_id_ = Id(model_, mjOBJ_JOINT, "object_free");
  camera_id_ = Id(model_, mjOBJ_CAMERA, "robot_camera");
  left_pad_id_ = Id(model_, mjOBJ_GEOM, "gr_left_pad1");
  right_pad_id_ = Id(model_, mjOBJ_GEOM, "gr_right_pad1");
  if (gripper_actuator_id_ < 0 || grip_site_id_ < 0 || ee_site_id_ < 0 ||
      object_body_id_ < 0 || camera_id_ < 0 || object_free_joint_id_ < 0) {
    if (error) *error = "missing benchmark scene element";
    return false;
  }
  return true;
}
bool SimEngine::Load(std::string* error) {
  std::lock_guard lock(mutex_);
  char buffer[2048]{};
  mjModel* model =
      mj_loadXML(scene_path_.c_str(), nullptr, buffer, sizeof(buffer));
  if (!model) {
    if (error) *error = buffer;
    return false;
  }
  if (data_) mj_deleteData(data_);
  if (model_) mj_deleteModel(model_);
  model_ = model;
  data_ = mj_makeData(model_);
  if (!data_) {
    if (error) *error = "mj_makeData failed";
    return false;
  }
  if (!ResolveIds(error)) return false;
  mj_resetData(model_, data_);
  for (int i = 0; i < 6; ++i)
    target_joint_[i] = data_->qpos[model_->jnt_qposadr[joint_ids_[i]]];
  mj_forward(model_, data_);
  return true;
}
bool SimEngine::Reset(std::uint64_t seed, std::string* error) {
  std::lock_guard lock(mutex_);
  if (!model_) {
    if (error) *error = "scene not loaded";
    return false;
  }
  mj_resetData(
      model_,
      data_);  // Stable integer mixing gives deterministic, bounded variants.
  auto mix = [&seed]() {
    seed += 0x9e3779b97f4a7c15ULL;
    auto z = seed;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
  };
  for (int i = 0; i < 3; ++i)
    data_->qpos[model_->jnt_qposadr[base_joint_ids_[i]]] = 0;
  const int freeadr = model_->jnt_qposadr[object_free_joint_id_];
  data_->qpos[freeadr + 0] = -0.03 + double(mix() % 600) / 10000.;
  data_->qpos[freeadr + 1] = -0.28 + double(mix() % 1700) / 10000.;
  data_->qpos[freeadr + 2] = 0.75;
  for (int i = 0; i < 2; ++i) {
    int g = Id(model_, mjOBJ_GEOM, i == 0 ? "obstacle_0" : "obstacle_1");
    if (g >= 0) {
      if (profile_ == BenchmarkProfile::Navigation) {
        model_->geom_pos[3 * g] = i == 0 ? -0.7 : -0.1;
        model_->geom_pos[3 * g + 1] =
            (i == 0 ? -0.45 : -0.75) + double(mix() % 1200) / 10000. - 0.06;
      } else {
        model_->geom_pos[3 * g] = i == 0 ? -0.65 : -0.45;
        model_->geom_pos[3 * g + 1] =
            (i == 0 ? -0.65 : 0.8) + double(mix() % 1200) / 10000. - 0.06;
      }
    }
  }
  data_->qpos[freeadr + 3] = 1;
  data_->qpos[freeadr + 4] = data_->qpos[freeadr + 5] =
      data_->qpos[freeadr + 6] = 0;
  const double home[] = {-1.5708, -1.5708, 1.5708, -1.5708, -1.5708, 0};
  for (int i = 0; i < 6; ++i) {
    data_->qpos[model_->jnt_qposadr[joint_ids_[i]]] = home[i];
    target_joint_[i] = home[i];
  }
  for (int i = 0; i < 6; ++i) {
    data_->ctrl[actuator_ids_[i]] = target_joint_[i];
  }
  data_->ctrl[gripper_actuator_id_] = 0;
  gripper_target_ = 0;
  base_drive_active_ = false;
  for (int i = 0; i < 3; ++i)
    base_hold_[i] = data_->qpos[model_->jnt_qposadr[base_joint_ids_[i]]];
  halted_ = false;
  lifted_contact_duration_s_ = 0;
  collision_active_ = false;
  collisions_ = 0;
  sequence_ = 0;
  ++interruption_epoch_;
  mj_forward(model_, data_);
  return true;
}
void SimEngine::StepLocked(int steps) {
  if (!model_ || !data_) return;
  for (int n = 0; n < steps; ++n) {
    if (base_drive_active_ && base_drive_until_s_ > 0 &&
        data_->time >= base_drive_until_s_) {
      base_drive_active_ = false;
      base_drive_until_s_ = 0;
      for (int i = 0; i < 3; ++i)
        base_hold_[i] = data_->qpos[model_->jnt_qposadr[base_joint_ids_[i]]];
    }
    for (int i = 0; i < 6; ++i)
      data_->ctrl[actuator_ids_[i]] = target_joint_[i];
    double yaw = data_->qpos[model_->jnt_qposadr[base_joint_ids_[2]]];
    double vx = std::cos(yaw) * base_drive_[0] - std::sin(yaw) * base_drive_[1];
    double vy = std::sin(yaw) * base_drive_[0] + std::cos(yaw) * base_drive_[1];
    if (base_drive_active_) {
      data_->ctrl[base_actuator_ids_[0]] = vx;
      data_->ctrl[base_actuator_ids_[1]] = vy;
      data_->ctrl[base_actuator_ids_[2]] = base_drive_[2];
    } else {
      for (int i = 0; i < 3; ++i) {
        int id = base_joint_ids_[i];
        double position = data_->qpos[model_->jnt_qposadr[id]];
        double velocity = data_->qvel[model_->jnt_dofadr[id]];
        double error = base_hold_[i] - position;
        data_->ctrl[base_actuator_ids_[i]] =
            std::clamp(6. * error - 0.5 * velocity, i == 2 ? -1.0 : -0.8,
                       i == 2 ? 1.0 : 0.8);
      }
    }
    data_->ctrl[gripper_actuator_id_] = gripper_target_;
    mj_step(model_, data_);
    ++sequence_;
    const int object_geom = Id(model_, mjOBJ_GEOM, "object_geom"),
              mobile = Id(model_, mjOBJ_BODY, "mobile_base");
    bool left = false, right = false, world_collision = false;
    for (int c = 0; c < data_->ncon; ++c) {
      auto& contact = data_->contact[c];
      int a = contact.geom[0], b = contact.geom[1];
      if ((a == object_geom && (b == left_pad_id_ || b == right_pad_id_)) ||
          (b == object_geom && (a == left_pad_id_ || a == right_pad_id_))) {
        left |= (a == left_pad_id_ || b == left_pad_id_);
        right |= (a == right_pad_id_ || b == right_pad_id_);
      }
      auto is_robot = [&](int geom) {
        int body = model_->geom_bodyid[geom];
        while (body > 0) {
          if (body == mobile) return true;
          body = model_->body_parentid[body];
        }
        return false;
      };
      auto is_hazard = [&](int geom) {
        return geom == Id(model_, mjOBJ_GEOM, "table") ||
               geom == Id(model_, mjOBJ_GEOM, "obstacle_0") ||
               geom == Id(model_, mjOBJ_GEOM, "obstacle_1");
      };
      if ((is_robot(a) && is_hazard(b)) || (is_robot(b) && is_hazard(a)))
        world_collision = true;
    }
    if (world_collision && !collision_active_) {
      ++collisions_;
    }
    collision_active_ = world_collision;
    if (left && right && gripper_target_ > 0 &&
        data_->xpos[3 * object_body_id_ + 2] > 0.82) {
      lifted_contact_duration_s_ += model_->opt.timestep;
    }
  }
}
void SimEngine::Step(int steps) {
  std::lock_guard lock(mutex_);
  StepLocked(std::clamp(steps, 0, 100000));
}
Snapshot SimEngine::SnapshotLocked() const {
  Snapshot s;
  if (!model_) return s;
  s.sequence = sequence_;
  s.simulation_time_s = data_->time;
  for (int k = 0; k < 3; ++k) {
    s.object_position[k] = data_->xpos[3 * object_body_id_ + k];
    s.pinch_position[k] = data_->site_xpos[3 * grip_site_id_ + k];
  }
  for (int i = 0; i < 2; ++i) {
    int g = Id(model_, mjOBJ_GEOM, i == 0 ? "obstacle_0" : "obstacle_1");
    if (g >= 0) {
      s.obstacle_positions[i][0] = model_->geom_pos[3 * g];
      s.obstacle_positions[i][1] = model_->geom_pos[3 * g + 1];
    }
  }
  for (int i = 0; i < 6; ++i) {
    int j = joint_ids_[i];
    s.joint_positions_rad[i] = data_->qpos[model_->jnt_qposadr[j]];
    s.joint_velocities_rad_s[i] = data_->qvel[model_->jnt_dofadr[j]];
  }
  for (int i = 0; i < 3; ++i) {
    int j = base_joint_ids_[i];
    s.base_pose[i] = data_->qpos[model_->jnt_qposadr[j]] + (i == 0 ? -1.2 : 0);
    s.base_velocity[i] = data_->qvel[model_->jnt_dofadr[j]];
  }
  double yaw = s.base_pose[2], wx = s.base_velocity[0], wy = s.base_velocity[1];
  s.base_velocity[0] = std::cos(yaw) * wx + std::sin(yaw) * wy;
  s.base_velocity[1] = -std::sin(yaw) * wx + std::cos(yaw) * wy;
  int mobile = Id(model_, mjOBJ_BODY, "mobile_base");
  const mjtNum* bp = data_->xpos + 3 * mobile;
  const mjtNum* wp = data_->site_xpos + 3 * ee_site_id_;
  s.ee_position = {
      std::cos(yaw) * (wp[0] - bp[0]) + std::sin(yaw) * (wp[1] - bp[1]),
      -std::sin(yaw) * (wp[0] - bp[0]) + std::cos(yaw) * (wp[1] - bp[1]),
      wp[2] - bp[2]};
  mjtNum world_q[4], base_q[4], base_inv[4], local_q[4];
  mju_mat2Quat(world_q, data_->site_xmat + 9 * ee_site_id_);
  mju_mat2Quat(base_q, data_->xmat + 9 * mobile);
  mju_negQuat(base_inv, base_q);
  mju_mulQuat(local_q, base_inv, world_q);
  s.ee_orientation_xyzw = Quaternion(local_q);
  std::vector<mjtNum> jacp(3 * model_->nv);
  mj_jacSite(model_, data_, jacp.data(), nullptr, ee_site_id_);
  double world_vel[3]{};
  for (int k = 0; k < 3; ++k)
    for (int j = 0; j < model_->nv; ++j)
      world_vel[k] += jacp[k * model_->nv + j] * data_->qvel[j];
  s.ee_linear_velocity = {
      std::cos(yaw) * world_vel[0] + std::sin(yaw) * world_vel[1],
      -std::sin(yaw) * world_vel[0] + std::cos(yaw) * world_vel[1],
      world_vel[2]};
  int driver = Id(model_, mjOBJ_JOINT, "gr_right_driver_joint");
  s.gripper_position_pct =
      driver >= 0
          ? 100. * std::clamp(
                       double(data_->qpos[model_->jnt_qposadr[driver]] / 0.8),
                       0., 1.)
          : 0;
  s.gripper_force_n = 0;  // Model actuation is uncalibrated; do not label
                          // simulator force as newtons.
  const int object_geom = Id(model_, mjOBJ_GEOM, "object_geom");
  bool left = false, right = false;
  for (int c = 0; c < data_->ncon; ++c) {
    auto& con = data_->contact[c];
    int a = con.geom[0], b = con.geom[1];
    if (a == object_geom || b == object_geom) {
      left |= (a == left_pad_id_ || b == left_pad_id_);
      right |= (a == right_pad_id_ || b == right_pad_id_);
    }
  }
  s.arm_contact = left || right;
  if (left && right && s.gripper_position_pct > 10)
    s.object_held_id = "benchmark_object";
  return s;
}
Snapshot SimEngine::GetSnapshot() const {
  std::lock_guard lock(mutex_);
  return SnapshotLocked();
}
Score SimEngine::GetScore() const {
  std::lock_guard lock(mutex_);
  Score s;
  if (!model_) return s;
  auto b = SnapshotLocked();
  if (profile_ == BenchmarkProfile::Navigation) {
    const mjtNum* goal = data_->site_xpos + 3 * goal_site_id_;
    s.navigation =
        std::hypot(b.base_pose[0] - goal[0], b.base_pose[1] - goal[1]) < 0.18 &&
        std::abs(b.base_pose[2]) < 0.15;
    s.collisions = collisions_;
    s.elapsed_s = data_->time;
    return s;
  }
  s.navigation = (b.base_pose[0] > -0.70 && b.base_pose[0] < -0.35 &&
                  std::abs(b.base_pose[1]) < 0.30);
  s.grasp = lifted_contact_duration_s_ >= 0.15;
  const mjtNum* p = data_->xpos + 3 * object_body_id_;
  s.placement = s.grasp && p[0] > -0.18 && p[0] < 0.06 && p[1] > 0.12 &&
                p[1] < 0.36 && p[2] > 0.71 && p[2] < 0.82 &&
                b.object_held_id.empty();
  s.collisions = collisions_;
  s.elapsed_s = data_->time;
  return s;
}
CommandResult SimEngine::Execute(const Command& c) {
  std::unique_lock lock(mutex_);
  if (!model_) return {false, "unavailable"};
  if (c.type == Command::Type::Halt) {
    halted_ = true;
    ++interruption_epoch_;
    base_drive_active_ = false;
    for (int i = 0; i < 3; ++i)
      base_hold_[i] = data_->qpos[model_->jnt_qposadr[base_joint_ids_[i]]];
    for (int i = 0; i < 6; ++i)
      target_joint_[i] = data_->qpos[model_->jnt_qposadr[joint_ids_[i]]];
    return {true, {}};
  }
  if (c.type == Command::Type::ArmStop || c.type == Command::Type::BaseStop ||
      c.type == Command::Type::GripperStop) {
    ++interruption_epoch_;
    if (c.type == Command::Type::BaseStop) {
      base_drive_active_ = false;
      for (int i = 0; i < 3; ++i)
        base_hold_[i] = data_->qpos[model_->jnt_qposadr[base_joint_ids_[i]]];
    } else if (c.type == Command::Type::ArmStop)
      for (int i = 0; i < 6; ++i)
        target_joint_[i] = data_->qpos[model_->jnt_qposadr[joint_ids_[i]]];
    else
      gripper_target_ = data_->ctrl[gripper_actuator_id_];
    return {true, {}};
  }
  if (halted_) return {false, "device_unavailable"};
  if (c.type == Command::Type::BaseDrive) {
    for (int i = 0; i < 3; ++i)
      if (!Finite(c.values[i]) || std::abs(c.values[i]) > (i == 2 ? 1.5 : 1.0))
        return {false, "out_of_range"};
    for (int i = 0; i < 3; ++i) base_drive_[i] = c.values[i];
    base_drive_until_s_ = c.values[3] > 0 ? data_->time + c.values[3] : 0;
    base_drive_active_ = true;
    return {true, {}};
  }
  active_motion_.store(true);
  struct MotionGuard {
    std::atomic_bool& flag;
    ~MotionGuard() { flag.store(false); }
  } motion_guard{active_motion_};
  std::array<double, 6> target{};
  bool arm = false;
  double timeout = 0;
  if (c.type == Command::Type::ArmMoveJ) {
    for (int i = 0; i < 6; ++i) {
      double v = c.values[i];
      int j = joint_ids_[i];
      if (!Finite(v) || v < model_->jnt_range[2 * j] ||
          v > model_->jnt_range[2 * j + 1])
        return {false, "out_of_range"};
      target[i] = v;
    }
    arm = true;
    timeout = 8;
  } else if (c.type == Command::Type::ArmMoveL) {
    for (double v : c.values)
      if (!Finite(v)) return {false, "invalid_pose"};
    mjtNum desired_local[] = {c.values[6], c.values[3], c.values[4],
                              c.values[5]};
    double norm = mju_norm(desired_local, 4);
    if (norm < 0.99 || norm > 1.01) return {false, "invalid_pose"};
    int mobile = Id(model_, mjOBJ_BODY, "mobile_base");
    const mjtNum* bp = data_->xpos + 3 * mobile;
    double yaw = data_->qpos[model_->jnt_qposadr[base_joint_ids_[2]]];
    double world_p[3] = {
        bp[0] + std::cos(yaw) * c.values[0] - std::sin(yaw) * c.values[1],
        bp[1] + std::sin(yaw) * c.values[0] + std::cos(yaw) * c.values[1],
        bp[2] + c.values[2]};
    mjtNum base_q[4], desired[4];
    mju_mat2Quat(base_q, data_->xmat + 9 * mobile);
    mju_mulQuat(desired, base_q, desired_local);
    const double* p = world_p;
    if (p[2] < 0.08 || p[2] > 1.5 || std::abs(p[0]) > 3 || std::abs(p[1]) > 3)
      return {false, "workspace"};
    mjData* work = mj_makeData(model_);
    if (!work) return {false, "internal"};
    mj_copyData(work, model_, data_);
    bool solved = false;
    const int nv = int(model_->nv);
    std::vector<mjtNum> jp(3 * nv), jr(3 * nv);
    for (int iter = 0; iter < 300; ++iter) {
      mj_forward(model_, work);
      const mjtNum* current = work->site_xpos + 3 * ee_site_id_;
      mjtNum actual_q[4], rot_err[3];
      mju_mat2Quat(actual_q, work->site_xmat + 9 * ee_site_id_);
      mju_subQuat(rot_err, desired, actual_q);
      double err[6] = {p[0] - current[0], p[1] - current[1], p[2] - current[2],
                       rot_err[0],        rot_err[1],        rot_err[2]};
      double position_norm = std::hypot(err[0], std::hypot(err[1], err[2]));
      double angle_norm = std::hypot(err[3], std::hypot(err[4], err[5]));
      if (position_norm < 0.008 && angle_norm < 0.04) {
        solved = true;
        break;
      }
      mj_jacSite(model_, work, jp.data(), jr.data(), ee_site_id_);
      double a[6][7]{};
      for (int i = 0; i < 6; ++i) {
        int dof = model_->jnt_dofadr[joint_ids_[i]];
        for (int j = 0; j < 6; ++j) {
          int dof2 = model_->jnt_dofadr[joint_ids_[j]];
          for (int k = 0; k < 3; ++k) {
            a[i][j] += jp[k * nv + dof] * jp[k * nv + dof2] +
                       0.5 * jr[k * nv + dof] * jr[k * nv + dof2];
          }
        }
        a[i][i] += 0.01;
        for (int k = 0; k < 3; ++k) {
          a[i][6] +=
              jp[k * nv + dof] * err[k] + 0.5 * jr[k * nv + dof] * err[k + 3];
        }
      }
      for (int i = 0; i < 6; ++i) {
        double pivot = a[i][i];
        if (std::abs(pivot) < 1e-9) continue;
        for (int j = i; j < 7; ++j) a[i][j] /= pivot;
        for (int k = 0; k < 6; ++k)
          if (k != i) {
            double factor = a[k][i];
            for (int j = i; j < 7; ++j) a[k][j] -= factor * a[i][j];
          }
      }
      for (int i = 0; i < 6; ++i) {
        int j = joint_ids_[i], adr = model_->jnt_qposadr[j];
        work->qpos[adr] =
            std::clamp(work->qpos[adr] + std::clamp(a[i][6], -0.08, 0.08),
                       model_->jnt_range[2 * j], model_->jnt_range[2 * j + 1]);
      }
    }
    bool collision = false;
    if (solved) {
      mj_forward(model_, work);
      int mobile_body = Id(model_, mjOBJ_BODY, "mobile_base");
      for (int ci = 0; ci < work->ncon; ++ci) {
        const mjContact& contact = work->contact[ci];
        int ga = contact.geom[0], gb = contact.geom[1];
        int body_a = model_->geom_bodyid[ga], body_b = model_->geom_bodyid[gb];
        auto is_arm = [&](int body) {
          while (body > 0) {
            if (body == mobile_body) return true;
            body = model_->body_parentid[body];
          }
          return false;
        };
        bool a_arm = is_arm(body_a), b_arm = is_arm(body_b);
        if ((a_arm && body_b == 0) || (b_arm && body_a == 0)) {
          collision = true;
          break;
        }
      }
      if (!collision)
        for (int i = 0; i < 6; ++i)
          target[i] = work->qpos[model_->jnt_qposadr[joint_ids_[i]]];
    }
    mj_deleteData(work);
    if (!solved) return {false, "unreachable"};
    if (collision) return {false, "collision"};
    arm = true;
    timeout = 8;
  } else if (c.type == Command::Type::BaseNavigateRelative) {
    double dx = c.values[0], dy = c.values[1], yaw = c.values[2];
    if (!Finite(dx) || !Finite(dy) || !Finite(yaw) || std::hypot(dx, dy) > 4 ||
        std::abs(yaw) > kPi)
      return {false, "out_of_range"};
    auto snap = SnapshotLocked();
    double heading = snap.base_pose[2];
    double tx =
        snap.base_pose[0] + std::cos(heading) * dx - std::sin(heading) * dy;
    double ty =
        snap.base_pose[1] + std::sin(heading) * dx + std::cos(heading) * dy;
    double tyaw = heading + yaw;
    auto epoch = interruption_epoch_;
    double start = data_->time;
    while (data_->time - start < 15) {
      if (interruption_epoch_ != epoch) return {false, "interrupted"};
      auto s = SnapshotLocked();
      double ex = tx - s.base_pose[0], ey = ty - s.base_pose[1],
             ea = tyaw - s.base_pose[2];
      if (std::hypot(ex, ey) < 0.025 && std::abs(ea) < 0.04) {
        base_drive_active_ = false;
        for (int i = 0; i < 3; ++i)
          base_hold_[i] = data_->qpos[model_->jnt_qposadr[base_joint_ids_[i]]];
        return {true, {}};
      }
      double body_ex =
          std::cos(s.base_pose[2]) * ex + std::sin(s.base_pose[2]) * ey;
      double body_ey =
          -std::sin(s.base_pose[2]) * ex + std::cos(s.base_pose[2]) * ey;
      base_drive_[0] = std::clamp(body_ex * 2., -0.6, 0.6);
      base_drive_[1] = std::clamp(body_ey * 2., -0.6, 0.6);
      base_drive_[2] = std::clamp(ea * 2., -1.0, 1.0);
      base_drive_active_ = true;
      int before = collisions_;
      StepLocked(10);
      if (collisions_ > before) {
        base_drive_active_ = false;
        for (int i = 0; i < 3; ++i)
          base_hold_[i] = data_->qpos[model_->jnt_qposadr[base_joint_ids_[i]]];
        return {false, "collision"};
      }
      lock.unlock();
      std::this_thread::sleep_for(std::chrono::microseconds(100));
      lock.lock();
    }
    base_drive_active_ = false;
    for (int i = 0; i < 3; ++i)
      base_hold_[i] = data_->qpos[model_->jnt_qposadr[base_joint_ids_[i]]];
    return {false, "timeout"};
  } else if (c.type == Command::Type::GripperMove) {
    if (!Finite(c.force_n) || c.force_n < 0) return {false, "out_of_range"};
    gripper_target_ = c.close ? 255. : 0;
    auto epoch = interruption_epoch_;
    double start = data_->time;
    while (data_->time - start < 2) {
      if (interruption_epoch_ != epoch) return {false, "interrupted"};
      StepLocked(10);
      auto state = SnapshotLocked();
      if (c.close ? (state.gripper_position_pct > 88 ||
                     !state.object_held_id.empty())
                  : state.gripper_position_pct < 8)
        return {true, {}};
      lock.unlock();
      std::this_thread::sleep_for(std::chrono::microseconds(100));
      lock.lock();
    }
    return {false, "timeout"};
  } else
    return {false, "unsupported"};
  if (arm) {
    for (int i = 0; i < 6; ++i) target_joint_[i] = target[i];
    auto epoch = interruption_epoch_;
    double start = data_->time;
    while (data_->time - start < timeout) {
      if (interruption_epoch_ != epoch) return {false, "interrupted"};
      StepLocked(10);
      bool done = true;
      for (int i = 0; i < 6; ++i)
        if (std::abs(data_->qpos[model_->jnt_qposadr[joint_ids_[i]]] -
                     target[i]) > 0.035)
          done = false;
      if (done) return {true, {}};
      lock.unlock();
      std::this_thread::sleep_for(std::chrono::microseconds(100));
      lock.lock();
    }
    return {false, "timeout"};
  }
  return {false, "unsupported"};
}
CameraFrame SimEngine::RenderCamera() {
  std::lock_guard lock(mutex_);
  CameraFrame frame;
  if (!model_ || render_failed_) return frame;
  frame.sequence = sequence_;
  frame.timestamp_ns = static_cast<std::int64_t>(data_->time * 1e9);
  if (!render_state_) {
    auto* r = new RenderState();
    using GetPlatformDisplay = PFNEGLGETPLATFORMDISPLAYEXTPROC;
    auto get_platform = reinterpret_cast<GetPlatformDisplay>(
        eglGetProcAddress("eglGetPlatformDisplayEXT"));
    r->display = get_platform ? get_platform(EGL_PLATFORM_SURFACELESS_MESA,
                                             EGL_DEFAULT_DISPLAY, nullptr)
                              : eglGetDisplay(EGL_DEFAULT_DISPLAY);
    EGLConfig config;
    EGLint count = 0;
    const EGLint attrs[] = {EGL_SURFACE_TYPE,
                            EGL_PBUFFER_BIT,
                            EGL_RENDERABLE_TYPE,
                            EGL_OPENGL_BIT,
                            EGL_RED_SIZE,
                            8,
                            EGL_GREEN_SIZE,
                            8,
                            EGL_BLUE_SIZE,
                            8,
                            EGL_DEPTH_SIZE,
                            24,
                            EGL_NONE};
    const EGLint pbattrs[] = {EGL_WIDTH, 640, EGL_HEIGHT, 480, EGL_NONE};
    bool valid = r->display != EGL_NO_DISPLAY &&
                 eglInitialize(r->display, nullptr, nullptr) &&
                 eglBindAPI(EGL_OPENGL_API) &&
                 eglChooseConfig(r->display, attrs, &config, 1, &count) &&
                 count > 0;
    if (valid) {
      r->surface = eglCreatePbufferSurface(r->display, config, pbattrs);
      r->context =
          eglCreateContext(r->display, config, EGL_NO_CONTEXT, nullptr);
      valid = r->surface != EGL_NO_SURFACE && r->context != EGL_NO_CONTEXT &&
              eglMakeCurrent(r->display, r->surface, r->surface, r->context);
    }
    if (!valid) {
      if (r->context != EGL_NO_CONTEXT)
        eglDestroyContext(r->display, r->context);
      if (r->surface != EGL_NO_SURFACE)
        eglDestroySurface(r->display, r->surface);
      if (r->display != EGL_NO_DISPLAY) eglTerminate(r->display);
      delete r;
      render_failed_ = true;
      return frame;
    }
    mjv_defaultScene(&r->scene);
    mjv_makeScene(model_, &r->scene, 2000);
    mjr_defaultContext(&r->render);
    using GetGlError = unsigned int (*)();
    auto gl_error =
        reinterpret_cast<GetGlError>(eglGetProcAddress("glGetError"));
    if (gl_error)
      while (gl_error() != 0) {
      }
    mjr_makeContext(model_, &r->render, mjFONTSCALE_100);
    render_state_ = r;
  } else if (!eglMakeCurrent(render_state_->display, render_state_->surface,
                             render_state_->surface, render_state_->context)) {
    render_failed_ = true;
    return frame;
  }
  auto* r = render_state_;
  mjvCamera camera;
  mjv_defaultCamera(&camera);
  camera.type = mjCAMERA_FIXED;
  camera.fixedcamid = camera_id_;
  mjvOption options;
  mjv_defaultOption(&options);
  mjvPerturb perturb;
  mjv_defaultPerturb(&perturb);
  mjv_updateScene(model_, data_, &options, &perturb, &camera, mjCAT_ALL,
                  &r->scene);
  mjrRect viewport{0, 0, 640, 480};
  mjr_setBuffer(mjFB_OFFSCREEN, &r->render);
  mjr_render(viewport, &r->scene, &r->render);
  std::vector<unsigned char> pixels(640 * 480 * 3), flipped(pixels.size());
  mjr_readPixels(pixels.data(), nullptr, viewport, &r->render);
  for (int y = 0; y < 480; ++y)
    std::memcpy(flipped.data() + y * 640 * 3,
                pixels.data() + (479 - y) * 640 * 3, 640 * 3);
  jpeg_compress_struct jpeg{};
  jpeg_error_mgr err{};
  jpeg.err = jpeg_std_error(&err);
  jpeg_create_compress(&jpeg);
  unsigned char* out = nullptr;
  unsigned long bytes = 0;
  jpeg_mem_dest(&jpeg, &out, &bytes);
  jpeg.image_width = 640;
  jpeg.image_height = 480;
  jpeg.input_components = 3;
  jpeg.in_color_space = JCS_RGB;
  jpeg_set_defaults(&jpeg);
  jpeg_set_quality(&jpeg, 85, TRUE);
  jpeg_start_compress(&jpeg, TRUE);
  while (jpeg.next_scanline < jpeg.image_height) {
    JSAMPROW row = flipped.data() + jpeg.next_scanline * 640 * 3;
    jpeg_write_scanlines(&jpeg, &row, 1);
  }
  jpeg_finish_compress(&jpeg);
  frame.jpeg.assign(out, out + bytes);
  frame.width = 640;
  frame.height = 480;
  std::free(out);
  jpeg_destroy_compress(&jpeg);
  eglMakeCurrent(r->display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
  return frame;
}
}  // namespace eos_mujoco
