#include "service.h"

#include <grpcpp/grpcpp.h>
#include <sys/stat.h>

#include <chrono>
#include <cmath>
#include <filesystem>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <thread>

#include "benchmark.grpc.pb.h"
#include "engine.h"
#include "gui.h"
#include "simulator.grpc.pb.h"
#include "v2_service.h"

namespace eos_mujoco {
namespace sim = ::eos::simulator::v1;
namespace bench = ::eos::mujoco::benchmark::v1;
namespace {

template <size_t N>
void Copy(const std::array<double, N>& source,
          google::protobuf::RepeatedField<double>* output) {
  for (double value : source) output->Add(value);
}
void FillBase(const Snapshot& snapshot, sim::BaseTelemetry* output) {
  output->set_x_m(snapshot.base_pose[0]);
  output->set_y_m(snapshot.base_pose[1]);
  output->set_yaw_rad(snapshot.base_pose[2]);
  output->set_linear_x_m_s(snapshot.base_velocity[0]);
  output->set_linear_y_m_s(snapshot.base_velocity[1]);
  output->set_angular_z_rad_s(snapshot.base_velocity[2]);
}
void FillState(const Snapshot& snapshot, bench::StateResponse* response) {
  response->set_ok(true);
  response->set_sequence(snapshot.sequence);
  response->set_elapsed_sim_s(snapshot.simulation_time_s);
  response->set_base_x_m(snapshot.base_pose[0]);
  response->set_base_y_m(snapshot.base_pose[1]);
  response->set_base_yaw_rad(snapshot.base_pose[2]);
  Copy(snapshot.joint_positions_rad, response->mutable_arm_joints_rad());
  response->set_object_held_id(snapshot.object_held_id);
  Copy(snapshot.object_position, response->mutable_object_position_m());
  Copy(snapshot.obstacle_positions[0],
       response->mutable_obstacle_0_position_m());
  Copy(snapshot.obstacle_positions[1],
       response->mutable_obstacle_1_position_m());
  Copy(snapshot.pinch_position, response->mutable_gripper_pinch_position_m());
}

bool KnownDevice(const std::string& id) {
  return id == "base-0" || id == "arm-0" || id == "cam-0" || id == "gripper-0";
}
bool CommandMatchesDevice(const sim::ExecuteRequest& request) {
  switch (request.command_case()) {
    case sim::ExecuteRequest::kArmMoveL:
    case sim::ExecuteRequest::kArmMoveJ:
    case sim::ExecuteRequest::kArmStop:
      return request.device_id() == "arm-0";
    case sim::ExecuteRequest::kBaseDrive:
    case sim::ExecuteRequest::kBaseNavigateRelative:
    case sim::ExecuteRequest::kBaseStop:
      return request.device_id() == "base-0";
    case sim::ExecuteRequest::kGripperMove:
    case sim::ExecuteRequest::kGripperStop:
      return request.device_id() == "gripper-0";
    case sim::ExecuteRequest::kHalt:
      return KnownDevice(request.device_id());
    default:
      return false;
  }
}
class SimulatorEndpoint final : public sim::SimulatorService::Service {
 public:
  SimulatorEndpoint(SimEngine& engine, std::atomic_bool& halted)
      : engine_(engine), halted_(halted) {}
  grpc::Status Health(grpc::ServerContext*, const sim::HealthRequest* request,
                      sim::HealthResponse* response) override {
    response->set_available(KnownDevice(request->device_id()) &&
                            !halted_.load());
    return grpc::Status::OK;
  }
  grpc::Status Execute(grpc::ServerContext*, const sim::ExecuteRequest* request,
                       sim::ExecuteResponse* response) override {
    if (request->device_id().empty())
      return {grpc::StatusCode::INVALID_ARGUMENT, "device_id is required"};
    if (!KnownDevice(request->device_id()) || !CommandMatchesDevice(*request)) {
      response->set_error_code("unsupported_device_command");
      return grpc::Status::OK;
    }
    Command command{};
    switch (request->command_case()) {
      case sim::ExecuteRequest::kArmMoveL: {
        const auto& pose = request->arm_move_l();
        if (pose.position_m_size() != 3 || pose.orientation_xyzw_size() != 4)
          return {grpc::StatusCode::INVALID_ARGUMENT,
                  "arm pose dimensions are invalid"};
        command.type = Command::Type::ArmMoveL;
        for (int i = 0; i < 3; ++i) command.values[i] = pose.position_m(i);
        for (int i = 0; i < 4; ++i)
          command.values[i + 3] = pose.orientation_xyzw(i);
        break;
      }
      case sim::ExecuteRequest::kArmMoveJ:
        if (request->arm_move_j().positions_rad_size() != 6)
          return {grpc::StatusCode::INVALID_ARGUMENT,
                  "arm joint dimensions are invalid"};
        command.type = Command::Type::ArmMoveJ;
        for (int i = 0; i < 6; ++i)
          command.values[i] = request->arm_move_j().positions_rad(i);
        break;
      case sim::ExecuteRequest::kArmStop:
        command.type = Command::Type::ArmStop;
        break;
      case sim::ExecuteRequest::kBaseDrive:
        command.type = Command::Type::BaseDrive;
        command.values[0] = request->base_drive().linear_x_m_s();
        command.values[1] = request->base_drive().linear_y_m_s();
        command.values[2] = request->base_drive().angular_z_rad_s();
        break;
      case sim::ExecuteRequest::kBaseNavigateRelative:
        command.type = Command::Type::BaseNavigateRelative;
        command.values[0] = request->base_navigate_relative().x_m();
        command.values[1] = request->base_navigate_relative().y_m();
        command.values[2] = request->base_navigate_relative().yaw_rad();
        command.values[3] =
            request->base_navigate_relative().footprint_width_m();
        command.values[4] =
            request->base_navigate_relative().footprint_length_m();
        break;
      case sim::ExecuteRequest::kBaseStop:
        command.type = Command::Type::BaseStop;
        break;
      case sim::ExecuteRequest::kGripperMove:
        command.type = Command::Type::GripperMove;
        command.close = request->gripper_move().close();
        command.force_n = request->gripper_move().force_n();
        break;
      case sim::ExecuteRequest::kGripperStop:
        command.type = Command::Type::GripperStop;
        break;
      case sim::ExecuteRequest::kHalt:
        command.type = Command::Type::Halt;
        break;
      case sim::ExecuteRequest::COMMAND_NOT_SET:
        return {grpc::StatusCode::INVALID_ARGUMENT, "command is required"};
      default:
        response->set_accepted(false);
        response->set_error_code("unsupported_command");
        return grpc::Status::OK;
    }
    if (halted_.load() && command.type != Command::Type::Halt) {
      response->set_error_code("device_unavailable");
      return grpc::Status::OK;
    }
    for (double value : command.values)
      if (!std::isfinite(value))
        return {grpc::StatusCode::INVALID_ARGUMENT,
                "command contains non-finite value"};
    const auto result = engine_.Execute(command);
    if (command.type == Command::Type::Halt && result.accepted)
      halted_.store(true);
    response->set_accepted(result.accepted);
    response->set_error_code(result.error_code);
    return grpc::Status::OK;
  }
  grpc::Status ReadTelemetry(grpc::ServerContext*,
                             const sim::ReadTelemetryRequest* request,
                             sim::ReadTelemetryResponse* response) override {
    if (halted_.load()) return grpc::Status::OK;
    if ((request->kind() == sim::ARM && request->device_id() != "arm-0") ||
        (request->kind() == sim::BASE && request->device_id() != "base-0") ||
        (request->kind() == sim::GRIPPER &&
         request->device_id() != "gripper-0"))
      return grpc::Status::OK;
    const Snapshot snapshot = engine_.GetSnapshot();
    switch (request->kind()) {
      case sim::ARM: {
        auto* out = response->mutable_arm();
        Copy(snapshot.ee_position, out->mutable_ee_position());
        Copy(snapshot.ee_orientation_xyzw, out->mutable_ee_orientation_xyzw());
        Copy(snapshot.ee_linear_velocity, out->mutable_ee_linear_velocity());
        Copy(snapshot.joint_positions_rad, out->mutable_joint_positions_rad());
        Copy(snapshot.joint_velocities_rad_s,
             out->mutable_joint_velocities_rad_s());
        out->set_contact(snapshot.arm_contact);
        break;
      }
      case sim::BASE:
        FillBase(snapshot, response->mutable_base());
        break;
      case sim::GRIPPER: {
        auto* out = response->mutable_gripper();
        out->set_jaw(!snapshot.object_held_id.empty()      ? 2
                     : snapshot.gripper_position_pct >= 95 ? 1
                                                           : 0);
        out->set_object_held_id(snapshot.object_held_id);
        out->set_force_n(snapshot.gripper_force_n);
        out->set_position_pct(snapshot.gripper_position_pct);
        break;
      }
      case sim::TELEMETRY_KIND_UNSPECIFIED:
        return {grpc::StatusCode::INVALID_ARGUMENT,
                "telemetry kind is required"};
      default:
        return grpc::Status::OK;
    }
    response->set_available(true);
    return grpc::Status::OK;
  }
  grpc::Status ReadCameraFrame(
      grpc::ServerContext*, const sim::ReadCameraFrameRequest* request,
      sim::ReadCameraFrameResponse* response) override {
    if (request->device_id() != "cam-0" || halted_.load())
      return grpc::Status::OK;
    const auto frame = engine_.RenderCamera();
    if (frame.jpeg.empty()) return grpc::Status::OK;
    const auto snapshot = engine_.GetSnapshot();
    response->set_available(true);
    response->set_width_px(frame.width);
    response->set_height_px(frame.height);
    response->set_source_timestamp_ns(frame.timestamp_ns);
    response->set_jpeg(frame.jpeg.data(), frame.jpeg.size());
    response->mutable_state()->set_sequence(frame.sequence);
    FillBase(snapshot, response->mutable_state()->mutable_base());
    response->mutable_state()->set_scene_revision(1);
    return grpc::Status::OK;
  }

 private:
  SimEngine& engine_;
  std::atomic_bool& halted_;
};

class BenchmarkEndpoint final : public bench::BenchmarkService::Service {
 public:
  BenchmarkEndpoint(SimEngine& engine, std::atomic_bool& halted,
                    std::atomic_bool& paused, std::mutex& clock_mutex)
      : engine_(engine),
        halted_(halted),
        paused_(paused),
        clock_mutex_(clock_mutex) {}
  grpc::Status Reset(grpc::ServerContext*, const bench::ResetRequest* request,
                     bench::StateResponse* response) override {
    std::lock_guard clock_lock(clock_mutex_);
    paused_.store(true);
    std::string error;
    if (!engine_.Reset(request->seed(), &error)) {
      response->set_error(error);
      return grpc::Status::OK;
    }
    halted_.store(false);
    FillState(engine_.GetSnapshot(), response);
    return grpc::Status::OK;
  }
  grpc::Status Step(grpc::ServerContext*, const bench::StepRequest* request,
                    bench::StateResponse* response) override {
    if (request->steps() > 100000)
      return {grpc::StatusCode::INVALID_ARGUMENT, "step count exceeds 100000"};
    std::lock_guard clock_lock(clock_mutex_);
    if (!paused_.load())
      return {grpc::StatusCode::FAILED_PRECONDITION,
              "pause simulation before manual stepping"};
    engine_.Step(request->steps());
    FillState(engine_.GetSnapshot(), response);
    return grpc::Status::OK;
  }
  grpc::Status State(grpc::ServerContext*, const bench::StateRequest*,
                     bench::StateResponse* response) override {
    FillState(engine_.GetSnapshot(), response);
    return grpc::Status::OK;
  }
  grpc::Status SetPaused(grpc::ServerContext*,
                         const bench::SetPausedRequest* request,
                         bench::StateResponse* response) override {
    std::lock_guard clock_lock(clock_mutex_);
    paused_.store(request->paused());
    FillState(engine_.GetSnapshot(), response);
    return grpc::Status::OK;
  }
  grpc::Status Score(grpc::ServerContext*, const bench::ScoreRequest*,
                     bench::ScoreResponse* response) override {
    const auto score = engine_.GetScore();
    response->set_navigation(score.navigation);
    response->set_grasp(score.grasp);
    response->set_placement(score.placement);
    response->set_collisions(score.collisions);
    response->set_elapsed_sim_s(score.elapsed_s);
    return grpc::Status::OK;
  }

 private:
  SimEngine& engine_;
  std::atomic_bool& halted_;
  std::atomic_bool& paused_;
  std::mutex& clock_mutex_;
};

std::unique_ptr<grpc::Server> StartServer(const std::filesystem::path& socket,
                                          grpc::Service* service) {
  std::filesystem::create_directories(socket.parent_path());
  std::error_code error;
  std::filesystem::remove(socket, error);
  grpc::ServerBuilder builder;
  builder.SetMaxReceiveMessageSize(1024 * 1024);
  builder.SetMaxSendMessageSize(9 * 1024 * 1024);
  builder.AddListeningPort("unix:" + socket.string(),
                           grpc::InsecureServerCredentials());
  builder.RegisterService(service);
  auto server = builder.BuildAndStart();
  if (!server) throw std::runtime_error("cannot listen on " + socket.string());
  if (::chmod(socket.c_str(), S_IRUSR | S_IWUSR) != 0) {
    server->Shutdown();
    throw std::runtime_error("cannot secure socket " + socket.string());
  }
  return server;
}
}  // namespace

void Serve(const std::filesystem::path& simulator_socket,
           const std::filesystem::path& benchmark_socket,
           const std::filesystem::path& v2_socket,
           const std::filesystem::path& scene, const std::atomic_bool& stop,
           bool manual_step, bool gui, bool managed_strict_socket) {
  SimEngine engine(scene.string());
  std::string error;
  if (!engine.Load(&error))
    throw std::runtime_error("scene load failed: " + error);
  if (!engine.Reset(0, &error))
    throw std::runtime_error("scene reset failed: " + error);
  if (managed_strict_socket) {
    const auto frame = engine.RenderCamera();
    if (frame.jpeg.empty()) throw std::runtime_error("managed_camera_unavailable");
  }
  std::atomic_bool halted{false};
  std::atomic_bool paused{manual_step};
  std::mutex clock_mutex;
  SimulatorEndpoint simulator(engine, halted);
  BenchmarkEndpoint benchmark(engine, halted, paused, clock_mutex);
  std::unique_ptr<grpc::Server> simulator_server;
  std::unique_ptr<V2Server> v2_server;
  std::unique_ptr<GuiWindow> live_window;
  std::unique_ptr<grpc::Server> benchmark_server;
  try {
    if (!managed_strict_socket) {
      simulator_server = StartServer(simulator_socket, &simulator);
      benchmark_server = StartServer(benchmark_socket, &benchmark);
    }
    if (!v2_socket.empty())
      v2_server = std::make_unique<V2Server>(v2_socket, engine,
                                             managed_strict_socket);
    if (gui) live_window = std::make_unique<GuiWindow>(engine);
    std::atomic_bool ticker_stop{false};
    std::thread ticker([&] {
      auto next = std::chrono::steady_clock::now();
      while (!ticker_stop.load() && !stop.load()) {
        next += std::chrono::milliseconds(2);
        {
          std::lock_guard clock_lock(clock_mutex);
          if (!paused.load()) engine.Step(1);
        }
        const auto now = std::chrono::steady_clock::now();
        if (next < now - std::chrono::milliseconds(20)) next = now;
        std::this_thread::sleep_until(next);
      }
    });
    while (!stop.load())
      std::this_thread::sleep_for(std::chrono::milliseconds(50));
    ticker_stop.store(true);
    ticker.join();
  } catch (...) {
    if (benchmark_server) benchmark_server->Shutdown();
    v2_server.reset();
    if (simulator_server) simulator_server->Shutdown();
    std::error_code ignored;
    std::filesystem::remove(benchmark_socket, ignored);
    std::filesystem::remove(simulator_socket, ignored);
    throw;
  }
  if (benchmark_server) benchmark_server->Shutdown();
  live_window.reset();
  v2_server.reset();
  if (simulator_server) simulator_server->Shutdown();
  std::error_code ignored;
  std::filesystem::remove(benchmark_socket, ignored);
  std::filesystem::remove(simulator_socket, ignored);
}
}  // namespace eos_mujoco
