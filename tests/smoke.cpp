#include <grpcpp/grpcpp.h>

#include <chrono>
#include <iostream>
#include <memory>
#include <string>
#include <thread>

#include "benchmark.grpc.pb.h"
#include "simulator.grpc.pb.h"

int main(int argc, char** argv) {
  if (argc != 3) return 2;
  auto simulator_channel =
      grpc::CreateChannel(std::string("unix:") + argv[1], grpc::InsecureChannelCredentials());
  auto benchmark_channel =
      grpc::CreateChannel(std::string("unix:") + argv[2], grpc::InsecureChannelCredentials());
  auto simulator = eos::simulator::v1::SimulatorService::NewStub(simulator_channel);
  auto benchmark = eos::mujoco::benchmark::v1::BenchmarkService::NewStub(benchmark_channel);
  eos::simulator::v1::HealthRequest health_request;
  health_request.set_device_id("arm-0");
  eos::simulator::v1::HealthResponse health_response;
  grpc::ClientContext health_context;
  health_context.set_deadline(std::chrono::system_clock::now() + std::chrono::seconds(5));
  if (!simulator->Health(&health_context, health_request, &health_response).ok() ||
      !health_response.available())
    return 3;
  eos::mujoco::benchmark::v1::ResetRequest reset_request;
  reset_request.set_seed(42);
  eos::mujoco::benchmark::v1::StateResponse reset_response;
  grpc::ClientContext reset_context;
  reset_context.set_deadline(std::chrono::system_clock::now() + std::chrono::seconds(5));
  if (!benchmark->Reset(&reset_context, reset_request, &reset_response).ok() ||
      !reset_response.ok() || reset_response.arm_joints_rad_size() != 6 ||
      reset_response.object_position_m_size() != 3 ||
      reset_response.obstacle_0_position_m_size() != 2 ||
      reset_response.obstacle_1_position_m_size() != 2 ||
      reset_response.gripper_pinch_position_m_size() != 3)
    return 4;
  eos::simulator::v1::ReadTelemetryRequest telemetry_request;
  telemetry_request.set_device_id("arm-0");
  telemetry_request.set_kind(eos::simulator::v1::ARM);
  eos::simulator::v1::ReadTelemetryResponse telemetry_response;
  grpc::ClientContext telemetry_context;
  telemetry_context.set_deadline(std::chrono::system_clock::now() + std::chrono::seconds(5));
  if (!simulator->ReadTelemetry(&telemetry_context, telemetry_request, &telemetry_response).ok() ||
      !telemetry_response.available() || telemetry_response.arm().joint_positions_rad_size() != 6)
    return 5;
  eos::simulator::v1::ReadCameraFrameRequest camera_request;
  camera_request.set_device_id("cam-0");
  eos::simulator::v1::ReadCameraFrameResponse camera_response;
  grpc::ClientContext camera_context;
  camera_context.set_deadline(std::chrono::system_clock::now() + std::chrono::seconds(10));
  if (!simulator->ReadCameraFrame(&camera_context, camera_request, &camera_response).ok() ||
      !camera_response.available() || camera_response.jpeg().size() < 4 ||
      static_cast<unsigned char>(camera_response.jpeg()[0]) != 0xff ||
      static_cast<unsigned char>(camera_response.jpeg()[1]) != 0xd8) {
    std::cerr << "camera unavailable: " << camera_response.available()
              << " jpeg=" << camera_response.jpeg().size() << "\n";
    return 8;
  }
  eos::mujoco::benchmark::v1::StepRequest step_request;
  step_request.set_steps(10);
  eos::mujoco::benchmark::v1::StateResponse step_response;
  grpc::ClientContext step_context;
  step_context.set_deadline(std::chrono::system_clock::now() + std::chrono::seconds(5));
  if (!benchmark->Step(&step_context, step_request, &step_response).ok() || !step_response.ok() ||
      step_response.elapsed_sim_s() <= reset_response.elapsed_sim_s())
    return 6;
  eos::simulator::v1::HealthRequest unknown_request;
  unknown_request.set_device_id("speaker-0");
  eos::simulator::v1::HealthResponse unknown_response;
  grpc::ClientContext unknown_context;
  if (!simulator->Health(&unknown_context, unknown_request, &unknown_response).ok() ||
      unknown_response.available())
    return 9;
  eos::mujoco::benchmark::v1::SetPausedRequest resume_request;
  resume_request.set_paused(false);
  eos::mujoco::benchmark::v1::StateResponse resume_response;
  grpc::ClientContext resume_context;
  if (!benchmark->SetPaused(&resume_context, resume_request, &resume_response).ok() ||
      !resume_response.ok())
    return 10;
  eos::simulator::v1::ExecuteRequest drive_request;
  drive_request.set_device_id("base-0");
  drive_request.mutable_base_drive()->set_linear_x_m_s(0.2);
  eos::simulator::v1::ExecuteResponse drive_response;
  grpc::ClientContext drive_context;
  if (!simulator->Execute(&drive_context, drive_request, &drive_response).ok() ||
      !drive_response.accepted())
    return 12;
  std::this_thread::sleep_for(std::chrono::milliseconds(50));
  eos::mujoco::benchmark::v1::StateRequest state_request;
  eos::mujoco::benchmark::v1::StateResponse realtime_response;
  grpc::ClientContext realtime_context;
  if (!benchmark->State(&realtime_context, state_request, &realtime_response).ok() ||
      realtime_response.elapsed_sim_s() <= step_response.elapsed_sim_s())
    return 11;
  eos::simulator::v1::ReadTelemetryRequest base_request;
  base_request.set_device_id("base-0");
  base_request.set_kind(eos::simulator::v1::BASE);
  eos::simulator::v1::ReadTelemetryResponse base_response;
  grpc::ClientContext base_context;
  if (!simulator->ReadTelemetry(&base_context, base_request, &base_response).ok() ||
      !base_response.available() || base_response.base().x_m() <= reset_response.base_x_m()) {
    std::cerr << "base x=" << base_response.base().x_m()
              << " vx=" << base_response.base().linear_x_m_s() << "\n";
    return 13;
  }
  eos::mujoco::benchmark::v1::ScoreRequest score_request;
  eos::mujoco::benchmark::v1::ScoreResponse score_response;
  grpc::ClientContext score_context;
  score_context.set_deadline(std::chrono::system_clock::now() + std::chrono::seconds(5));
  if (!benchmark->Score(&score_context, score_request, &score_response).ok()) return 7;
  eos::simulator::v1::ExecuteRequest halt_request;
  halt_request.set_device_id("base-0");
  halt_request.mutable_halt();
  eos::simulator::v1::ExecuteResponse halt_response;
  grpc::ClientContext halt_context;
  if (!simulator->Execute(&halt_context, halt_request, &halt_response).ok() ||
      !halt_response.accepted())
    return 14;
  eos::simulator::v1::HealthResponse halted_response;
  grpc::ClientContext halted_context;
  if (!simulator->Health(&halted_context, health_request, &halted_response).ok() ||
      halted_response.available())
    return 15;
  eos::mujoco::benchmark::v1::StateResponse restart_response;
  grpc::ClientContext restart_context;
  if (!benchmark->Reset(&restart_context, reset_request, &restart_response).ok() ||
      !restart_response.ok())
    return 16;
  eos::simulator::v1::HealthResponse healthy_again;
  grpc::ClientContext healthy_again_context;
  if (!simulator->Health(&healthy_again_context, health_request, &healthy_again).ok() ||
      !healthy_again.available())
    return 17;
  std::cout << "smoke ok: sim_time=" << step_response.elapsed_sim_s() << "\n";
  return 0;
}
