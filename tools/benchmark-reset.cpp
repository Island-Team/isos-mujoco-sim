#include <grpcpp/grpcpp.h>

#include <chrono>
#include <iostream>
#include <stdexcept>
#include <string>

#include "benchmark.grpc.pb.h"

int main(int argc, char** argv) {
  try {
    if (argc != 3) throw std::invalid_argument("usage: benchmark-reset SOCKET SEED");
    const std::string path = argv[1];
    if (path.empty() || path.front() != '/')
      throw std::invalid_argument("absolute socket required");
    std::size_t parsed = 0;
    const std::string seed_text = argv[2];
    if (seed_text.empty() || seed_text.front() == '-') throw std::invalid_argument("invalid seed");
    const auto seed = std::stoull(seed_text, &parsed);
    if (parsed != seed_text.size()) throw std::invalid_argument("invalid seed");
    auto channel = grpc::CreateChannel("unix:" + path, grpc::InsecureChannelCredentials());
    if (!channel->WaitForConnected(std::chrono::system_clock::now() + std::chrono::seconds(5)))
      throw std::runtime_error("benchmark socket unavailable");
    auto stub = eos::mujoco::benchmark::v1::BenchmarkService::NewStub(channel);
    eos::mujoco::benchmark::v1::ResetRequest request;
    request.set_seed(seed);
    eos::mujoco::benchmark::v1::StateResponse response;
    grpc::ClientContext context;
    context.set_deadline(std::chrono::system_clock::now() + std::chrono::seconds(5));
    const auto status = stub->Reset(&context, request, &response);
    if (!status.ok()) throw std::runtime_error("Reset: " + status.error_message());
    if (!response.ok()) throw std::runtime_error("Reset: " + response.error());
    std::cout << "{\"ok\":true,\"seed\":" << seed << ",\"sequence\":" << response.sequence()
              << ",\"elapsed_sim_s\":" << response.elapsed_sim_s() << "}\n";
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "benchmark-reset: " << error.what() << '\n';
    return 1;
  }
}
