#include <grpcpp/grpcpp.h>

#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>

#include "benchmark.grpc.pb.h"

namespace {
namespace bench = eos::mujoco::benchmark::v1;

struct Options {
  std::filesystem::path socket;
  std::string task;
  std::uint64_t seed = 0;
  double duration_s = 0;
};

void Usage() {
  std::cout << "Usage: benchmark-eval --benchmark-socket PATH --task pick-place|navigation "
               "--seed N --duration-s SECONDS\n";
}

Options Parse(int argc, char** argv) {
  Options out;
  bool has_seed = false;
  for (int i = 1; i < argc; ++i) {
    const std::string key = argv[i];
    if (key == "--help") {
      Usage();
      std::exit(0);
    }
    if (i + 1 >= argc) throw std::invalid_argument("missing value for " + key);
    const std::string value = argv[++i];
    if (key == "--benchmark-socket") {
      out.socket = value;
    } else if (key == "--task") {
      out.task = value;
    } else if (key == "--seed") {
      std::size_t used = 0;
      out.seed = std::stoull(value, &used);
      if (used != value.size() || value[0] == '-') throw std::invalid_argument("invalid seed");
      has_seed = true;
    } else if (key == "--duration-s") {
      std::size_t used = 0;
      out.duration_s = std::stod(value, &used);
      if (used != value.size()) throw std::invalid_argument("invalid duration");
    } else {
      throw std::invalid_argument("unknown option: " + key);
    }
  }
  if (!out.socket.is_absolute()) throw std::invalid_argument("benchmark socket must be absolute");
  if (out.task != "pick-place" && out.task != "navigation")
    throw std::invalid_argument("task must be pick-place or navigation");
  if (!has_seed) throw std::invalid_argument("seed is required");
  if (!std::isfinite(out.duration_s) || out.duration_s <= 0 || out.duration_s > 3600)
    throw std::invalid_argument("duration-s must be in (0, 3600]");
  return out;
}

template <typename Request, typename Response>
void Call(bench::BenchmarkService::Stub& stub,
          grpc::Status (bench::BenchmarkService::Stub::*method)(grpc::ClientContext*,
                                                                const Request&, Response*),
          const Request& request, Response* response, const char* name) {
  grpc::ClientContext context;
  context.set_deadline(std::chrono::system_clock::now() + std::chrono::seconds(10));
  const grpc::Status status = (stub.*method)(&context, request, response);
  if (!status.ok()) throw std::runtime_error(std::string(name) + ": " + status.error_message());
}

void CheckState(const bench::StateResponse& state, const char* name) {
  if (!state.ok()) throw std::runtime_error(std::string(name) + ": " + state.error());
}
}  // namespace

int main(int argc, char** argv) {
  try {
    const Options options = Parse(argc, argv);
    auto channel =
        grpc::CreateChannel("unix:" + options.socket.string(), grpc::InsecureChannelCredentials());
    if (!channel->WaitForConnected(std::chrono::system_clock::now() + std::chrono::seconds(10)))
      throw std::runtime_error("benchmark socket is unavailable");
    auto stub = bench::BenchmarkService::NewStub(channel);

    bench::ResetRequest reset_request;
    reset_request.set_seed(options.seed);
    bench::StateResponse reset_response;
    Call(*stub, &bench::BenchmarkService::Stub::Reset, reset_request, &reset_response, "Reset");
    CheckState(reset_response, "Reset");

    bench::SetPausedRequest resume_request;
    resume_request.set_paused(false);
    bench::StateResponse resume_response;
    Call(*stub, &bench::BenchmarkService::Stub::SetPaused, resume_request, &resume_response,
         "SetPaused(false)");
    CheckState(resume_response, "SetPaused(false)");
    std::this_thread::sleep_for(std::chrono::duration<double>(options.duration_s));

    bench::SetPausedRequest pause_request;
    pause_request.set_paused(true);
    bench::StateResponse pause_response;
    Call(*stub, &bench::BenchmarkService::Stub::SetPaused, pause_request, &pause_response,
         "SetPaused(true)");
    CheckState(pause_response, "SetPaused(true)");

    bench::ScoreRequest score_request;
    bench::ScoreResponse score;
    Call(*stub, &bench::BenchmarkService::Stub::Score, score_request, &score, "Score");
    const bool success = options.task == "navigation"
                             ? score.navigation()
                             : score.navigation() && score.grasp() && score.placement();
    std::cout << std::boolalpha << "{\"task\":\"" << options.task << "\",\"seed\":" << options.seed
              << ",\"success\":" << success << ",\"navigation\":" << score.navigation()
              << ",\"grasp\":" << score.grasp() << ",\"placement\":" << score.placement()
              << ",\"collisions\":" << score.collisions()
              << ",\"elapsed_sim_s\":" << score.elapsed_sim_s() << "}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "benchmark-eval: " << error.what() << '\n';
    return 1;
  }
}
