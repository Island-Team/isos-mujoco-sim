#include "v2_service.h"

#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
#include <poll.h>
#include <sys/random.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

#include <algorithm>
#include <array>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <limits>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "engine.h"
#include "scene_devices.h"

namespace eos_mujoco {
namespace {
using Struct = google::protobuf::Struct;
using Value = google::protobuf::Value;
constexpr std::uint32_t kMaxMetadata = 65536;
constexpr std::uint32_t kMaxPayload = 8 * 1024 * 1024;

bool ReadAll(int fd, void* buffer, size_t length) {
  auto* bytes = static_cast<unsigned char*>(buffer);
  while (length) {
    const auto count = ::read(fd, bytes, length);
    if (count <= 0) return false;
    bytes += count;
    length -= static_cast<size_t>(count);
  }
  return true;
}
bool ReadAllUntil(int fd, void* buffer, size_t length,
                  std::chrono::steady_clock::time_point deadline) {
  auto* bytes = static_cast<unsigned char*>(buffer);
  while (length) {
    const auto left = std::chrono::duration_cast<std::chrono::milliseconds>(
                          deadline - std::chrono::steady_clock::now())
                          .count();
    if (left <= 0) return false;
    pollfd event{fd, POLLIN, 0};
    if (::poll(&event, 1, static_cast<int>(left)) <= 0) return false;
    const auto count = ::recv(fd, bytes, length, MSG_DONTWAIT);
    if (count < 0 && (errno == EINTR || errno == EAGAIN)) continue;
    if (count <= 0) return false;
    bytes += count;
    length -= static_cast<size_t>(count);
  }
  return true;
}
bool WriteAll(int fd, const void* buffer, size_t length) {
  const auto* bytes = static_cast<const unsigned char*>(buffer);
  while (length) {
    const auto count = ::send(fd, bytes, length, MSG_NOSIGNAL);
    if (count <= 0) return false;
    bytes += count;
    length -= static_cast<size_t>(count);
  }
  return true;
}
std::uint32_t Decode32(const unsigned char* bytes) {
  return std::uint32_t(bytes[0]) | (std::uint32_t(bytes[1]) << 8) |
         (std::uint32_t(bytes[2]) << 16) | (std::uint32_t(bytes[3]) << 24);
}
void Encode32(std::uint32_t value, unsigned char* bytes) {
  for (int i = 0; i < 4; ++i) bytes[i] = static_cast<unsigned char>(value >> (8 * i));
}
const Value* Field(const Struct& value, const char* key) {
  const auto it = value.fields().find(key);
  return it == value.fields().end() ? nullptr : &it->second;
}
std::string String(const Struct& value, const char* key) {
  const auto* field = Field(value, key);
  return field && field->kind_case() == Value::kStringValue ? field->string_value() : "";
}
bool Number(const Struct& value, const char* key, double* output) {
  const auto* field = Field(value, key);
  if (!field || field->kind_case() != Value::kNumberValue || !std::isfinite(field->number_value()))
    return false;
  *output = field->number_value();
  return true;
}
void Set(Struct* value, const char* key, const std::string& text) {
  (*value->mutable_fields())[key].set_string_value(text);
}
void Set(Struct* value, const char* key, const char* text) { Set(value, key, std::string(text)); }
void Set(Struct* value, const char* key, double number) {
  (*value->mutable_fields())[key].set_number_value(number);
}
void Set(Struct* value, const char* key, bool boolean) {
  (*value->mutable_fields())[key].set_bool_value(boolean);
}
template <size_t N>
void SetArray(Struct* value, const char* key, const std::array<double, N>& values) {
  auto* list = (*value->mutable_fields())[key].mutable_list_value();
  for (double number : values) list->add_values()->set_number_value(number);
}
void Reject(Struct* reply, const std::string& message) {
  Set(reply, "ok", false);
  Set((*reply->mutable_fields())["error"].mutable_struct_value(), "message", message);
}
void RejectStrict(Struct* reply, const char* code, const char* message) {
  Reject(reply, message);
  Set((*reply->mutable_fields())["error"].mutable_struct_value(), "code", code);
}
void SendReply(int fd, const Struct& reply) {
  std::string encoded;
  unsigned char header[8];
  if (!google::protobuf::util::MessageToJsonString(reply, &encoded).ok() || encoded.empty() ||
      encoded.size() > kMaxMetadata)
    return;
  Encode32(static_cast<std::uint32_t>(encoded.size()), header);
  Encode32(0, header + 4);
  WriteAll(fd, header, sizeof(header)) && WriteAll(fd, encoded.data(), encoded.size());
}
bool BoundedId(const Struct& request, const char* key) {
  const auto* field = Field(request, key);
  return field && field->kind_case() == Value::kStringValue && !field->string_value().empty() &&
         field->string_value().size() <= 128;
}
const char* OperationKind(const std::string& op) {
  if (op == "health") return "";
  if (op == "camera_capture") return "camera";
  if (op == "base_observe" || op == "base_move") return "base";
  if (op == "manipulator_observe" || op == "manipulator_move") return "manipulator";
  if (op == "stop") return "actuator";
  return nullptr;
}
std::string Fingerprint(const std::string& op, const std::array<double, 7>& values, int count) {
  std::ostringstream stream;
  stream << op;
  for (int i = 0; i < count; ++i)
    stream << ':' << std::setprecision(17) << (values[i] == 0 ? 0.0 : values[i]);
  return stream.str();
}
bool CanonicalEpoch(const std::string& token, std::uint64_t* parsed) {
  if (token.empty() || token.size() > 20 || (token.size() > 1 && token[0] == '0')) return false;
  std::uint64_t value = 0;
  for (char digit : token) {
    if (digit < '0' || digit > '9' ||
        value > (std::numeric_limits<std::uint64_t>::max() - (digit - '0')) / 10)
      return false;
    value = value * 10 + (digit - '0');
  }
  *parsed = value;
  return true;
}
std::string NewGenerationId() {
  std::array<unsigned char, 16> random{};
  size_t filled = 0;
  while (filled < random.size()) {
    const auto count = ::getrandom(random.data() + filled, random.size() - filled, 0);
    if (count < 0 && errno == EINTR) continue;
    if (count <= 0) throw std::runtime_error("generation_random_unavailable");
    filled += static_cast<size_t>(count);
  }
  std::ostringstream stream;
  stream << std::hex << std::setfill('0');
  for (unsigned char byte : random) stream << std::setw(2) << static_cast<unsigned>(byte);
  return stream.str();
}
void Handle(int fd, SimEngine& engine) {
  unsigned char header[8];
  if (!ReadAll(fd, header, sizeof(header))) return;
  const auto metadata_size = Decode32(header);
  const auto payload_size = Decode32(header + 4);
  if (!metadata_size || metadata_size > kMaxMetadata || payload_size) return;
  std::string body(metadata_size, '\0');
  if (!ReadAll(fd, body.data(), body.size())) return;
  Struct request;
  if (!google::protobuf::util::JsonStringToMessage(body, &request).ok()) return;
  Struct reply;
  Set(&reply, "version", "2.0.0");
  Set(&reply, "id", String(request, "id"));
  Set(&reply, "ok", true);
  const auto snapshot = engine.GetSnapshot();
  Set(&reply, "timestamp_ns", snapshot.simulation_time_s * 1e9);
  Set(&reply, "sequence", static_cast<double>(snapshot.sequence));
  std::vector<std::uint8_t> payload;
  if (String(request, "version") != "2.0.0" || String(request, "id").empty()) {
    Reject(&reply, "invalid protocol version or request ID");
  } else {
    const auto op = String(request, "op");
    if (op == "health") {
      Set(&reply, "accepted", true);
    } else if (op == "camera_capture") {
      const auto frame = engine.RenderCamera();
      if (frame.jpeg.empty())
        Reject(&reply, "camera render unavailable");
      else {
        Set(&reply, "format", "jpeg");
        Set(&reply, "rgb_length", static_cast<double>(frame.jpeg.size()));
        Set(&reply, "depth_available", false);
        Set(&reply, "width_px", static_cast<double>(frame.width));
        Set(&reply, "height_px", static_cast<double>(frame.height));
        Set(&reply, "timestamp_ns", static_cast<double>(frame.timestamp_ns));
        Set(&reply, "sequence", static_cast<double>(frame.sequence));
        payload = frame.jpeg;
      }
    } else if (op == "base_observe") {
      SetArray(&reply, "position_m",
               std::array<double, 2>{snapshot.base_pose[0], snapshot.base_pose[1]});
      SetArray(&reply, "linear_velocity_m_s",
               std::array<double, 2>{snapshot.base_velocity[0], snapshot.base_velocity[1]});
      Set(&reply, "yaw_rad", snapshot.base_pose[2]);
      Set(&reply, "angular_velocity_rad_s", snapshot.base_velocity[2]);
    } else if (op == "manipulator_observe") {
      SetArray(&reply, "joint_positions_rad", snapshot.joint_positions_rad);
      SetArray(&reply, "joint_velocities_rad_s", snapshot.joint_velocities_rad_s);
      SetArray(&reply, "end_position_m", snapshot.ee_position);
      SetArray(&reply, "end_orientation_xyzw", snapshot.ee_orientation_xyzw);
    } else if (op == "base_move") {
      Command command{Command::Type::BaseDrive};
      double duration = 0;
      if (!Number(request, "linear_x_m_s", &command.values[0]) ||
          !Number(request, "linear_y_m_s", &command.values[1]) ||
          !Number(request, "angular_z_rad_s", &command.values[2]) ||
          !Number(request, "valid_for_ms", &duration) || duration <= 0 || duration > 5000) {
        Reject(&reply, "invalid base movement");
      } else {
        command.values[3] = duration / 1000.0;
        const auto result = engine.Execute(command);
        Set(&reply, "accepted", result.accepted);
        if (!result.accepted) Reject(&reply, result.error_code);
      }
    } else if (op == "manipulator_move") {
      Command command{Command::Type::ArmMoveJ};
      const auto* positions = Field(request, "joint_positions_rad");
      if (!positions || positions->kind_case() != Value::kListValue ||
          positions->list_value().values_size() != 6) {
        Reject(&reply, "joint_positions_rad must contain six values");
      } else {
        bool valid = true;
        for (int i = 0; i < 6; ++i) {
          const auto& field = positions->list_value().values(i);
          valid &= field.kind_case() == Value::kNumberValue && std::isfinite(field.number_value());
          command.values[i] = field.number_value();
        }
        if (!valid)
          Reject(&reply, "invalid joint position");
        else {
          const auto result = engine.Execute(command);
          Set(&reply, "accepted", result.accepted);
          if (!result.accepted) Reject(&reply, result.error_code);
        }
      }
    } else if (op == "stop") {
      const auto base = engine.Execute(Command{Command::Type::BaseStop});
      const auto arm = engine.Execute(Command{Command::Type::ArmStop});
      Set(&reply, "accepted", base.accepted && arm.accepted);
      if (!base.accepted || !arm.accepted) Reject(&reply, "stop failed");
    } else {
      Reject(&reply, "unsupported operation");
    }
  }
  std::string encoded;
  if (!google::protobuf::util::MessageToJsonString(reply, &encoded).ok() ||
      encoded.size() > kMaxMetadata || payload.size() > kMaxPayload)
    return;
  Encode32(static_cast<std::uint32_t>(encoded.size()), header);
  Encode32(static_cast<std::uint32_t>(payload.size()), header + 4);
  WriteAll(fd, header, sizeof(header)) && WriteAll(fd, encoded.data(), encoded.size()) &&
      WriteAll(fd, payload.data(), payload.size());
}
}  // namespace

void V2Server::HandleStrict(int fd, bool stop_lane) {
  if (!stop_lane && normal_ingress_.fetch_add(1) >= 8) {
    normal_ingress_.fetch_sub(1);
    return;
  }
  struct IngressGuard {
    std::atomic_int* count;
    ~IngressGuard() {
      if (count) count->fetch_sub(1);
    }
  } ingress{stop_lane ? nullptr : &normal_ingress_};
  unsigned char header[8];
  const auto ingress_deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(250);
  if (!ReadAllUntil(fd, header, sizeof(header), ingress_deadline)) return;
  const auto metadata_size = Decode32(header);
  if (!metadata_size || metadata_size > kMaxMetadata || Decode32(header + 4)) return;
  std::string body(metadata_size, '\0');
  if (!ReadAllUntil(fd, body.data(), body.size(), ingress_deadline)) return;
  Struct request;
  if (!google::protobuf::util::JsonStringToMessage(body, &request).ok()) return;
  const auto frame_ready = std::chrono::steady_clock::now();
  if (ingress.count) {
    ingress.count->fetch_sub(1);
    ingress.count = nullptr;
  }
  Struct reply;
  Set(&reply, "version", "2.0.0");
  Set(&reply, "id", String(request, "id"));
  Set(&reply, "ok", true);
  Snapshot snapshot;
  if (String(request, "op") != "stop" && String(request, "op") != "health")
    snapshot = engine_.GetSnapshot();
  Set(&reply, "timestamp_ns", snapshot.simulation_time_s * 1e9);
  Set(&reply, "sequence", static_cast<double>(snapshot.sequence));
  const auto fail = [&](const char* code, const char* message) {
    RejectStrict(&reply, code, message);
    SendReply(fd, reply);
  };
  if (!BoundedId(request, "id")) {
    fail("invalid_request", "id must contain 1..128 UTF-8 bytes");
    return;
  }
  if (String(request, "version") != "2.0.0") {
    fail("unsupported_version", "unsupported protocol version");
    return;
  }
  const auto op = String(request, "op");
  if (stop_lane && op != "health" && op != "stop") {
    fail("unsupported_operation", "stop lane accepts only health and stop");
    return;
  }
  const char* kind = OperationKind(op);
  if (!kind) {
    fail("unsupported_operation", "unsupported operation");
    return;
  }
  const auto node = String(request, "node");
  bool matched = false;
  for (const auto& device : kSceneDevices) {
    if (node == device.id && scene_profile_ == device.profile &&
        (std::strcmp(kind, "") == 0 || kind == std::string(device.kind) ||
         (std::strcmp(kind, "actuator") == 0 && (std::strcmp(device.kind, "base") == 0 ||
                                                 std::strcmp(device.kind, "manipulator") == 0)))) {
      matched = true;
      break;
    }
  }
  if (!matched) {
    fail("node_mismatch", "node is not the declared scene device for operation");
    return;
  }
  if (op != "base_move" && op != "manipulator_move" && op != "stop" &&
      Field(request, "command_id")) {
    fail("invalid_request", "command_id is only valid for motion and stop");
    return;
  }
  if (op == "health") {
    if (stop_lane && node != "base-0" && node != "arm-0") {
      fail("node_mismatch", "stop lane health requires an actuator node");
      return;
    }
    if (node == "cam-0") {
      const auto frame = engine_.RenderCamera();
      if (frame.jpeg.empty() || frame.width <= 0 || frame.height <= 0 || frame.width > 4096 ||
          frame.height > 4096 || frame.jpeg.size() > kMaxPayload) {
        fail("device_unavailable", "camera render unavailable");
        return;
      }
    }
    Set(&reply, "accepted", true);
    (*reply.mutable_fields())["features"].mutable_list_value()->add_values()->set_string_value(
        "strict-socket-v1");
    if (stop_lane || node != "cam-0")
      (*reply.mutable_fields())["features"].mutable_list_value()->add_values()->set_string_value(
          "strict-stop-v1");
    Set(&reply, "generation_id", generation_id_);
    SendReply(fd, reply);
    return;
  }
  if (op == "base_observe") {
    SetArray(&reply, "position_m",
             std::array<double, 2>{snapshot.base_pose[0], snapshot.base_pose[1]});
    SetArray(&reply, "linear_velocity_m_s",
             std::array<double, 2>{snapshot.base_velocity[0], snapshot.base_velocity[1]});
    Set(&reply, "yaw_rad", snapshot.base_pose[2]);
    Set(&reply, "angular_velocity_rad_s", snapshot.base_velocity[2]);
    SendReply(fd, reply);
    return;
  }
  if (op == "manipulator_observe") {
    SetArray(&reply, "joint_positions_rad", snapshot.joint_positions_rad);
    SetArray(&reply, "joint_velocities_rad_s", snapshot.joint_velocities_rad_s);
    SetArray(&reply, "end_position_m", snapshot.ee_position);
    SetArray(&reply, "end_orientation_xyzw", snapshot.ee_orientation_xyzw);
    SendReply(fd, reply);
    return;
  }
  if (op == "camera_capture") {
    const auto capture_epoch = engine_.StopEpoch();
    const auto frame = engine_.RenderCamera(capture_epoch);
    if (frame.jpeg.empty() || frame.width <= 0 || frame.height <= 0 || frame.width > 4096 ||
        frame.height > 4096 || frame.jpeg.size() > kMaxPayload) {
      fail("device_unavailable", "camera render unavailable");
      return;
    }
    Set(&reply, "format", "jpeg");
    Set(&reply, "rgb_length", static_cast<double>(frame.jpeg.size()));
    Set(&reply, "depth_available", false);
    Set(&reply, "width_px", static_cast<double>(frame.width));
    Set(&reply, "height_px", static_cast<double>(frame.height));
    Set(&reply, "timestamp_ns", static_cast<double>(frame.timestamp_ns));
    Set(&reply, "sequence", static_cast<double>(frame.sequence));
    std::string encoded;
    if (!google::protobuf::util::MessageToJsonString(reply, &encoded).ok() ||
        encoded.size() > kMaxMetadata)
      return;
    std::lock_guard publication_lock(publication_mutex_);
    if (capture_epoch != engine_.StopEpoch()) {
      fail("device_unavailable", "camera capture crossed stop fence");
      return;
    }
    {
      std::lock_guard capture_lock(capture_fd_mutex_);
      active_capture_fd_ = ::dup(fd);
    }
    if (active_capture_fd_ < 0 || capture_epoch != engine_.StopEpoch()) {
      std::lock_guard capture_lock(capture_fd_mutex_);
      if (active_capture_fd_ >= 0) ::close(active_capture_fd_);
      active_capture_fd_ = -1;
      fail("device_unavailable", "camera capture crossed stop fence");
      return;
    }
    Encode32(static_cast<std::uint32_t>(encoded.size()), header);
    Encode32(static_cast<std::uint32_t>(frame.jpeg.size()), header + 4);
    WriteAll(fd, header, sizeof(header)) && WriteAll(fd, encoded.data(), encoded.size()) &&
        WriteAll(fd, frame.jpeg.data(), frame.jpeg.size());
    {
      std::lock_guard capture_lock(capture_fd_mutex_);
      ::close(active_capture_fd_);
      active_capture_fd_ = -1;
    }
    return;
  }
  if (!BoundedId(request, "command_id")) {
    fail("invalid_command_id", "command_id must contain 1..128 UTF-8 bytes");
    return;
  }
  Command command{Command::Type::BaseDrive};
  std::array<double, 7> values{};
  int count = 0;
  if (op == "base_move") {
    const char* fields[] = {"linear_x_m_s", "linear_y_m_s", "angular_z_rad_s", "valid_for_ms"};
    for (int i = 0; i < 4; ++i) {
      if (!Number(request, fields[i], &values[i])) {
        fail("invalid_movement", "base movement requires finite numbers");
        return;
      }
    }
    if (std::abs(values[0]) > 1 || std::abs(values[1]) > 1 || std::abs(values[2]) > 1.5 ||
        values[3] <= 0 || values[3] > 5000) {
      fail("out_of_range", "base movement exceeds scene limits");
      return;
    }
    for (int i = 0; i < 3; ++i) command.values[i] = values[i];
    command.values[3] = values[3] / 1000.0;
    count = 4;
  } else if (op == "manipulator_move") {
    command.type = Command::Type::ArmMoveJ;
    const auto* positions = Field(request, "joint_positions_rad");
    if (!positions || positions->kind_case() != Value::kListValue ||
        positions->list_value().values_size() != 6) {
      fail("invalid_movement", "joint_positions_rad requires six numbers");
      return;
    }
    for (int i = 0; i < 6; ++i) {
      const auto& position = positions->list_value().values(i);
      if (position.kind_case() != Value::kNumberValue || !std::isfinite(position.number_value())) {
        fail("invalid_movement", "joint_positions_rad requires finite numbers");
        return;
      }
      command.values[i] = values[i] = position.number_value();
    }
    std::array<double, 6> targets{};
    std::copy_n(values.begin(), 6, targets.begin());
    if (!engine_.JointTargetsInRange(targets)) {
      fail("out_of_range", "joint target exceeds loaded model limits");
      return;
    }
    count = 6;
  }
  const auto command_id = String(request, "command_id");
  const bool stop = op == "stop";
  const auto requested_generation = String(request, "generation_id");
  if ((!stop || stop_lane || Field(request, "generation_id")) &&
      requested_generation != generation_id_) {
    fail("stale_generation", "request generation does not match this child");
    return;
  }
  std::uint64_t requested_epoch = 0;
  std::string epoch_token;
  if (!stop) {
    epoch_token = String(request, "stop_epoch");
    if (!CanonicalEpoch(epoch_token, &requested_epoch)) {
      fail("stop_fenced", "movement requires a canonical stop epoch");
      return;
    }
  }
  const auto fingerprint = Fingerprint(op, values, count) + (stop ? "" : ":epoch=" + epoch_token);
  StrictLedger::Reservation reservation;
  std::future<StopProof> stop_future;
  std::uint64_t reserved_stop_epoch = 0;
  const auto stop_started = frame_ready;
  {
    std::lock_guard lock(ledger_mutex_);
    reservation =
        ledger_.Reserve(node, command_id, stop, fingerprint,
                        stop || (!stop_inhibited_ && requested_epoch == engine_.StopEpoch()),
                        !stop || pending_stop_jobs_.load() < 8);
    if (stop && reservation.admission == StrictLedger::Admission::New) {
      stop_inhibited_ = true;
      reserved_stop_epoch = engine_.ReserveManagedStopEpoch();
      CancelActiveCapture();
      auto job = std::make_shared<StopJob>();
      job->epoch = reserved_stop_epoch;
      stop_future = job->result.get_future();
      pending_stop_jobs_.fetch_add(1);
      {
        std::lock_guard queue_lock(stop_jobs_mutex_);
        stop_jobs_.push_back(std::move(job));
      }
      stop_jobs_ready_.notify_one();
    }
  }
  if (reservation.admission == StrictLedger::Admission::Conflict) {
    fail("command_id_conflict", "command_id has conflicting operation");
    return;
  }
  if (reservation.admission == StrictLedger::Admission::InProgress) {
    fail("command_in_progress", "command is still in progress");
    return;
  }
  if (reservation.admission == StrictLedger::Admission::Capacity) {
    fail("command_capacity", "command retention capacity reached");
    return;
  }
  if (reservation.admission == StrictLedger::Admission::Stale) {
    fail("stop_fenced", "movement stop epoch is stale");
    return;
  }
  if (reservation.admission == StrictLedger::Admission::Prior) {
    Set(&reply, "timestamp_ns", reservation.result.timestamp_ns);
    Set(&reply, "sequence", static_cast<double>(reservation.result.sequence));
    Set(&reply, "accepted", reservation.result.accepted);
    if (stop) {
      Set(&reply, "base_stop", reservation.result.base_stop);
      Set(&reply, "arm_stop", reservation.result.arm_stop);
      Set(&reply, "generation_id", generation_id_);
      Set(&reply, "stop_epoch", reservation.result.stop_epoch);
    }
    if (!reservation.result.accepted)
      RejectStrict(&reply, reservation.result.error_code.c_str(),
                   reservation.result.error_message.c_str());
    SendReply(fd, reply);
    return;
  }
  bool accepted = false;
  std::string error_code = "device_unavailable";
  std::string error_message = "engine outcome uncertain";
  std::string base_stop, arm_stop, result_epoch;
  double result_timestamp = snapshot.simulation_time_s * 1e9;
  std::uint64_t result_sequence = snapshot.sequence;
  try {
    if (op == "stop") {
      const auto deadline = stop_started + std::chrono::seconds(1);
      base_stop = arm_stop = "unknown";
      result_epoch = std::to_string(reserved_stop_epoch);
      if (stop_future.wait_until(deadline) == std::future_status::ready) {
        const auto proof = stop_future.get();
        base_stop = proof.base_stopped ? "stopped" : "unknown";
        arm_stop = proof.arm_stopped ? "stopped" : "unknown";
        result_timestamp = proof.snapshot.simulation_time_s * 1e9;
        result_sequence = proof.snapshot.sequence;
        if (proof.base_stopped && proof.arm_stopped &&
            publication_mutex_.try_lock_until(deadline)) {
          accepted = std::chrono::steady_clock::now() <= deadline && !stop_unknown_latched_.load();
          publication_mutex_.unlock();
        }
      }
      error_code = "stop_outcome_unknown";
      error_message = "base or arm stop outcome unknown";
      if (!accepted && base_stop == "stopped" && arm_stop == "stopped")
        base_stop = arm_stop = "unknown";
    } else {
      const auto outcome = engine_.Execute(command, requested_epoch);
      accepted = outcome.accepted;
      error_code =
          (outcome.error_code == "command_interrupted" || outcome.error_code == "interrupted")
              ? "command_interrupted"
          : outcome.error_code == "out_of_range" ? "out_of_range"
                                                 : "device_unavailable";
      error_message = accepted
                          ? ""
                          : (error_code == "command_interrupted" ? "movement crossed the stop fence"
                             : error_code == "out_of_range" ? "movement exceeds loaded scene limits"
                                                            : "movement outcome uncertain");
    }
  } catch (...) {
    accepted = false;
    error_code = stop ? "stop_outcome_unknown" : "device_unavailable";
    error_message = stop ? "base or arm stop outcome unknown" : "engine outcome uncertain";
    if (stop) {
      base_stop = arm_stop = "unknown";
      result_epoch = std::to_string(reserved_stop_epoch);
    }
  }
  {
    std::lock_guard lock(ledger_mutex_);
    if (stop) {
      if (!accepted)
        stop_unknown_latched_.store(true);
      else if (!stop_unknown_latched_.load() && pending_stop_jobs_.load() == 0 &&
               engine_.StopEpoch() == reserved_stop_epoch)
        stop_inhibited_ = false;
    }
    ledger_.Finish(node, command_id, stop, accepted, error_code, error_message, result_timestamp,
                   result_sequence, base_stop, arm_stop, result_epoch);
  }
  Set(&reply, "timestamp_ns", result_timestamp);
  Set(&reply, "sequence", static_cast<double>(result_sequence));
  Set(&reply, "accepted", accepted);
  if (stop) {
    Set(&reply, "base_stop", base_stop);
    Set(&reply, "arm_stop", arm_stop);
    Set(&reply, "generation_id", generation_id_);
    Set(&reply, "stop_epoch", result_epoch);
  }
  if (!accepted) RejectStrict(&reply, error_code.c_str(), error_message.c_str());
  SendReply(fd, reply);
}

V2Server::V2Server(const std::filesystem::path& socket, SimEngine& engine,
                   bool managed_strict_socket)
    : socket_(socket), engine_(engine), managed_strict_socket_(managed_strict_socket) {
  scene_profile_ = engine_.SceneProfile();
  std::filesystem::create_directories(socket_.parent_path());
  if (managed_strict_socket_) {
    stop_socket_ = socket_.string() + ".stop";
    generation_id_ = NewGenerationId();
  }
  if (socket_.string().size() >= sizeof(sockaddr_un::sun_path) ||
      (managed_strict_socket_ && stop_socket_.string().size() >= sizeof(sockaddr_un::sun_path)))
    throw std::invalid_argument("socket_path_too_long");
  const auto bind_listener = [](const std::filesystem::path& path) {
    const int listener = ::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (listener < 0) throw std::runtime_error("cannot create v2 socket");
    sockaddr_un address{};
    address.sun_family = AF_UNIX;
    std::strcpy(address.sun_path, path.c_str());
    std::error_code ignored;
    std::filesystem::remove(path, ignored);
    if (::bind(listener, reinterpret_cast<sockaddr*>(&address), sizeof(address)) < 0 ||
        ::chmod(path.c_str(), S_IRUSR | S_IWUSR) < 0 || ::listen(listener, 16) < 0) {
      ::close(listener);
      std::filesystem::remove(path, ignored);
      throw std::runtime_error("cannot bind or secure v2 socket");
    }
    return listener;
  };
  listener_ = bind_listener(socket_);
  try {
    if (managed_strict_socket_) stop_listener_ = bind_listener(stop_socket_);
  } catch (...) {
    ::close(listener_);
    std::error_code ignored;
    std::filesystem::remove(socket_, ignored);
    throw;
  }
  if (managed_strict_socket_) {
    for (int i = 0; i < 32; ++i) normal_workers_.emplace_back([this] { Work(false); });
    for (int i = 0; i < 2; ++i) stop_workers_.emplace_back([this] { Work(true); });
    stop_executor_ = std::thread([this] { StopWork(); });
    stop_worker_ = std::thread([this] { Run(stop_listener_, true); });
  }
  worker_ = std::thread([this] { Run(listener_, false); });
}
V2Server::~V2Server() {
  stopping_.store(true);
  ::shutdown(listener_, SHUT_RDWR);
  ::close(listener_);
  if (stop_listener_ >= 0) {
    ::shutdown(stop_listener_, SHUT_RDWR);
    ::close(stop_listener_);
  }
  if (worker_.joinable()) worker_.join();
  if (stop_worker_.joinable()) stop_worker_.join();
  queue_ready_.notify_all();
  for (auto& worker : normal_workers_) worker.join();
  for (auto& worker : stop_workers_) worker.join();
  stop_jobs_ready_.notify_all();
  if (stop_executor_.joinable()) stop_executor_.join();
  std::error_code ignored;
  std::filesystem::remove(socket_, ignored);
  if (managed_strict_socket_) std::filesystem::remove(stop_socket_, ignored);
}
void V2Server::Run(int listener, bool stop_lane) {
  while (!stopping_.load()) {
    const int fd = ::accept4(listener, nullptr, nullptr, SOCK_CLOEXEC);
    if (fd < 0) continue;
    if (managed_strict_socket_) {
      bool queued = false;
      {
        std::lock_guard lock(queue_mutex_);
        auto& outstanding = stop_lane ? stop_outstanding_ : normal_outstanding_;
        auto& queue = stop_lane ? stop_queue_ : normal_queue_;
        if (outstanding < (stop_lane ? 10u : 32u)) {
          ++outstanding;
          queue.push_back(fd);
          queued = true;
        }
      }
      if (queued)
        queue_ready_.notify_all();
      else
        ::close(fd);
      continue;
    }
    timeval timeout{2, 0};
    ::setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    ::setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
    Handle(fd, engine_);
    ::close(fd);
  }
}
void V2Server::Work(bool stop_lane) {
  while (true) {
    int fd = -1;
    {
      std::unique_lock lock(queue_mutex_);
      queue_ready_.wait(lock, [&] {
        return stopping_.load() || !(stop_lane ? stop_queue_ : normal_queue_).empty();
      });
      auto& queue = stop_lane ? stop_queue_ : normal_queue_;
      if (queue.empty()) return;
      fd = queue.front();
      queue.pop_front();
    }
    timeval timeout{2, 0};
    ::setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
    HandleStrict(fd, stop_lane);
    ::close(fd);
    {
      std::lock_guard lock(queue_mutex_);
      --(stop_lane ? stop_outstanding_ : normal_outstanding_);
    }
  }
}
void V2Server::StopWork() {
  while (true) {
    std::shared_ptr<StopJob> job;
    {
      std::unique_lock lock(stop_jobs_mutex_);
      stop_jobs_ready_.wait(lock, [&] { return stopping_.load() || !stop_jobs_.empty(); });
      if (stop_jobs_.empty()) return;
      job = std::move(stop_jobs_.front());
      stop_jobs_.pop_front();
    }
    try {
      auto proof = engine_.ManagedStop(job->epoch);
      pending_stop_jobs_.fetch_sub(1);
      job->result.set_value(std::move(proof));
    } catch (...) {
      pending_stop_jobs_.fetch_sub(1);
      job->result.set_exception(std::current_exception());
    }
  }
}
void V2Server::CancelActiveCapture() {
  std::lock_guard lock(capture_fd_mutex_);
  if (active_capture_fd_ >= 0) ::shutdown(active_capture_fd_, SHUT_RDWR);
}
}  // namespace eos_mujoco
