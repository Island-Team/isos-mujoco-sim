#include "isos_node_v1.h"
#include "isos_node_v2.h"

#include <google/protobuf/struct.pb.h>
#include <google/protobuf/util/json_util.h>
#include <google/protobuf/stubs/strutil.h>
#include <poll.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include <array>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <cmath>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

using google::protobuf::Struct;
using google::protobuf::Value;

struct isos_node_handle {
  const isos_node_host_v1* host;
  std::mutex mutex;
  std::string socket;
  std::string device;
  std::string kind;
  std::string run_id;
  std::string revision;
  std::string generation_id;
  std::string service_instance;
  bool started = false;
  bool stopped = false;
  std::uint64_t request = 0;
};

namespace {
const Value* field(const Struct& object, const char* name) {
  auto it = object.fields().find(name);
  return it == object.fields().end() ? nullptr : &it->second;
}
std::string string_field(const Struct& object, const char* name) {
  auto* value = field(object, name);
  return value && value->kind_case() == Value::kStringValue ? value->string_value() : "";
}
const Struct* object_field(const Struct& object, const char* name) {
  auto* value = field(object, name);
  return value && value->kind_case() == Value::kStructValue ? &value->struct_value() : nullptr;
}
void set(Struct* object, const char* name, const std::string& value) {
  (*object->mutable_fields())[name].set_string_value(value);
}
void set(Struct* object, const char* name, double value) {
  (*object->mutable_fields())[name].set_number_value(value);
}
bool parse(const std::uint8_t* bytes, std::size_t length, Struct* result) {
  if (!bytes || length == 0 || length > 65536) return false;
  auto status = google::protobuf::util::JsonStringToMessage(
      std::string(reinterpret_cast<const char*>(bytes), length), result);
  return status.ok();
}
bool read_exact(int fd, void* data, std::size_t length) {
  auto* cursor = static_cast<unsigned char*>(data);
  while (length) {
    pollfd event{fd, POLLIN, 0};
    if (::poll(&event, 1, 1000) <= 0) return false;
    const auto count = ::recv(fd, cursor, length, MSG_DONTWAIT);
    if (count <= 0) return false;
    cursor += count;
    length -= static_cast<std::size_t>(count);
  }
  return true;
}
bool write_exact(int fd, const void* data, std::size_t length) {
  auto* cursor = static_cast<const unsigned char*>(data);
  while (length) {
    pollfd event{fd, POLLOUT, 0};
    if (::poll(&event, 1, 1000) <= 0) return false;
    const auto count = ::send(fd, cursor, length, MSG_NOSIGNAL | MSG_DONTWAIT);
    if (count <= 0) return false;
    cursor += count;
    length -= static_cast<std::size_t>(count);
  }
  return true;
}
std::uint32_t decode(const std::array<unsigned char, 8>& header, int offset) {
  return std::uint32_t(header[offset]) | (std::uint32_t(header[offset + 1]) << 8) |
         (std::uint32_t(header[offset + 2]) << 16) | (std::uint32_t(header[offset + 3]) << 24);
}
void encode(std::array<unsigned char, 8>* header, std::uint32_t size) {
  for (int i = 0; i < 4; ++i) (*header)[i] = static_cast<unsigned char>(size >> (i * 8));
}
bool exchange(isos_node_handle* node, const char* op, Struct* response,
              std::vector<unsigned char>* payload, const Struct* extra = nullptr) {
  if (node->socket.empty() || node->socket.size() >= sizeof(sockaddr_un::sun_path)) return false;
  Struct request;
  set(&request, "version", "2.0.0");
  set(&request, "id", "plugin-" + std::to_string(++node->request));
  set(&request, "node", node->device);
  set(&request, "op", op);
  if (extra) {
    for (const auto& [key, value] : extra->fields()) {
      if (key != "version" && key != "id" && key != "node" && key != "op")
        (*request.mutable_fields())[key] = value;
    }
  }
  std::string json;
  if (!google::protobuf::util::MessageToJsonString(request, &json).ok() || json.size() > 65536)
    return false;
  int fd = ::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
  if (fd < 0) return false;
  sockaddr_un address{};
  address.sun_family = AF_UNIX;
  std::memcpy(address.sun_path, node->socket.c_str(), node->socket.size() + 1);
  if (::connect(fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) != 0) {
    if (errno != EINPROGRESS) { ::close(fd); return false; }
    pollfd event{fd, POLLOUT, 0};
    int error = 0;
    socklen_t size = sizeof(error);
    if (::poll(&event, 1, 1000) <= 0 || ::getsockopt(fd, SOL_SOCKET, SO_ERROR, &error, &size) != 0 || error) {
      ::close(fd); return false;
    }
  }
  std::array<unsigned char, 8> header{};
  encode(&header, static_cast<std::uint32_t>(json.size()));
  bool ok = write_exact(fd, header.data(), header.size()) && write_exact(fd, json.data(), json.size()) &&
            read_exact(fd, header.data(), header.size());
  if (!ok) { ::close(fd); return false; }
  const auto meta_size = decode(header, 0);
  const auto payload_size = decode(header, 4);
  if (meta_size == 0 || meta_size > 65536 || payload_size > 8388608) { ::close(fd); return false; }
  std::string metadata(meta_size, '\0');
  payload->resize(payload_size);
  ok = read_exact(fd, metadata.data(), metadata.size()) &&
       (payload->empty() || read_exact(fd, payload->data(), payload->size()));
  ::close(fd);
  if (!ok || !google::protobuf::util::JsonStringToMessage(metadata, response).ok()) return false;
  auto* success = field(*response, "ok");
  return success && success->kind_case() == Value::kBoolValue && success->bool_value() &&
         string_field(*response, "id") == string_field(request, "id");
}
bool strict_health_impl(isos_node_handle* node) {
  Struct reply;
  std::vector<unsigned char> payload;
  if (!exchange(node, "health", &reply, &payload) || !payload.empty() ||
      string_field(reply, "version") != "2.0.0") return false;
  auto* accepted = field(reply, "accepted");
  auto* features = field(reply, "features");
  if (!accepted || accepted->kind_case() != Value::kBoolValue || !accepted->bool_value() ||
      !features || features->kind_case() != Value::kListValue) return false;
  const auto generation = string_field(reply, "generation_id");
  if (!generation.empty()) {
    if (!node->generation_id.empty() && node->generation_id != generation) return false;
    node->generation_id = generation;
  }
  for (const auto& item : features->list_value().values())
    if (item.kind_case() == Value::kStringValue && item.string_value() == "strict-socket-v1") return true;
  return false;
}
int32_t create_impl(const std::uint8_t* config, std::size_t length,
               const isos_node_host_v1* host, isos_node_handle** out) {
  if (!host || host->abi_version != ISOS_NODE_ABI_VERSION ||
      host->struct_size < sizeof(isos_node_host_v1) || !host->emit || !out) return -1;
  Struct document;
  if (!parse(config, length, &document)) return -1;
  const Struct* instance = object_field(document, "instance");
  if (!instance) instance = &document;
  const Struct* profile = object_field(*instance, "node");
  if (profile) instance = profile;
  const Struct* adapter = object_field(*instance, "adapter");
  const Struct* settings = adapter ? object_field(*adapter, "settings") : nullptr;
  if (!settings) settings = object_field(document, "settings");
  if (!settings) return -1;
  auto node = std::make_unique<isos_node_handle>();
  node->host = host;
  node->socket = string_field(*settings, "socket_path");
  if (node->socket.empty()) node->socket = string_field(document, "service_endpoint");
  node->device = string_field(*settings, "simulator_node");
  if (node->device.empty()) node->device = string_field(*settings, "device_id");
  const auto type = string_field(*instance, "node_type");
  if (type == "eos.hardware.camera.device@v0.2") node->kind = "camera";
  if (type == "eos.hardware.base.device@v0.2") node->kind = "base";
  if (type == "eos.hardware.manipulator.device@v0.2") node->kind = "manipulator";
  if (type == "eos.hardware.gripper.binary@v0.2") node->kind = "gripper";
  if (type == "eos.hardware.base.normalized_axes@v0.2") node->kind = "base";
  if (type == "eos.hardware.manipulator.normalized_cartesian@v0.2") node->kind = "manipulator";
  if (type == "eos.hardware.torso.normalized_axes@v0.2") node->kind = "torso";
  node->run_id = string_field(document, "run_id");
  node->revision = string_field(document, "revision");
  node->generation_id = string_field(document, "generation_id");
  node->service_instance = string_field(*settings, "service_instance");
  if (node->socket.empty() || node->device.empty() || node->kind.empty()) return -1;
  *out = node.release();
  return 0;
}
int32_t start_impl(isos_node_handle* node) {
  if (!node) return -1;
  std::lock_guard lock(node->mutex);
  if (node->stopped || !strict_health_impl(node)) return -1;
  node->started = true;
  return 0;
}
int32_t health_impl(isos_node_handle* node) {
  return node && node->started && !node->stopped && strict_health_impl(node) ? 1 : -1;
}
int32_t input_impl(isos_node_handle* node, const std::uint8_t* bytes, std::size_t length) {
  if (!node) return -1;
  std::lock_guard lock(node->mutex);
  if (!node->started || node->stopped) return -1;
  Struct request;
  if (!parse(bytes, length, &request) || string_field(request, "op") != "observe") return -1;
  if (node->service_instance == "robocasa") {
    Struct reply;
    std::vector<unsigned char> binary;
    if (!exchange(node, "observe", &reply, &binary)) return -1;
    const Struct* values = object_field(reply, "values");
    const auto* sequence = field(reply, "sequence");
    const auto* timestamp = field(reply, "timestamp_ns");
    if ((!values && node->kind != "camera") || !sequence || !timestamp || sequence->kind_case() != Value::kNumberValue ||
        timestamp->kind_case() != Value::kNumberValue) return -1;
    if (node->kind != "camera" && !binary.empty()) return -1;
    Struct envelope;
    set(&envelope, "port", node->kind == "camera" ? "frame" : "state");
    Struct* data = (*envelope.mutable_fields())["payload"].mutable_struct_value();
    Struct* sample = (*data->mutable_fields())["sample"].mutable_struct_value();
    if (!std::isfinite(timestamp->number_value()) || timestamp->number_value() < 0 ||
        !std::isfinite(sequence->number_value()) || sequence->number_value() < 0) return -1;
    set(sample, "source_time_ns", std::round(timestamp->number_value()));
    set(sample, "sequence", std::round(sequence->number_value()));
    set(sample, "clock", "monotonic");
    set(sample, "frame_id", node->kind == "base" ? "world" :
                            node->kind == "manipulator" ? "robot_base" : node->device);
    if (node->kind == "base" || node->kind == "manipulator") {
      const char* position_key = node->kind == "base" ? "base_position" : "end_effector_position_relative";
      const char* rotation_key = node->kind == "base" ? "base_rotation" : "end_effector_rotation_relative";
      const auto* position = field(*values, position_key);
      const auto* rotation = field(*values, rotation_key);
      if (!position || !rotation || position->kind_case() != Value::kListValue ||
          rotation->kind_case() != Value::kListValue ||
          position->list_value().values_size() != 3 || rotation->list_value().values_size() != 4)
        return -1;
      double norm = 0;
      for (const auto& element : position->list_value().values())
        if (element.kind_case() != Value::kNumberValue || !std::isfinite(element.number_value())) return -1;
      for (const auto& element : rotation->list_value().values()) {
        if (element.kind_case() != Value::kNumberValue || !std::isfinite(element.number_value())) return -1;
        norm += element.number_value() * element.number_value();
      }
      if (std::abs(norm - 1.0) > 0.02) return -1;
      *(*data->mutable_fields())["position_m"].mutable_list_value() = position->list_value();
      *(*data->mutable_fields())["orientation_xyzw"].mutable_list_value() = rotation->list_value();
    } else if (node->kind == "gripper") {
      const auto* positions = field(*values, "gripper_qpos");
      if (!positions || positions->kind_case() != Value::kListValue ||
          positions->list_value().values_size() != 2) return -1;
      auto* channels = (*data->mutable_fields())["channels"].mutable_list_value();
      for (int i = 0; i < 2; ++i) {
        const auto& value = positions->list_value().values(i);
        if (value.kind_case() != Value::kNumberValue || !std::isfinite(value.number_value())) return -1;
        Struct* channel = channels->add_values()->mutable_struct_value();
        set(channel, "name", i == 0 ? "left_finger" : "right_finger");
        set(channel, "value", value.number_value());
        set(channel, "unit", "m");
      }
    } else if (node->kind == "camera") {
      const auto* width_value = field(reply, "width_px");
      const auto* height_value = field(reply, "height_px");
      if (!width_value || !height_value || width_value->kind_case() != Value::kNumberValue ||
          height_value->kind_case() != Value::kNumberValue) return -1;
      const double width_number = width_value->number_value();
      const double height_number = height_value->number_value();
      if (std::floor(width_number) != width_number || std::floor(height_number) != height_number ||
          width_number < 64 || width_number > 512 || height_number < 64 || height_number > 512) return -1;
      const int width = static_cast<int>(width_number);
      const int height = static_cast<int>(height_number);
      if (binary.size() != static_cast<std::size_t>(width) * height * 3) return -1;
      std::string encoded;
      google::protobuf::Base64Escape(
          std::string(reinterpret_cast<const char*>(binary.data()), binary.size()), &encoded);
      set(data, "width_px", width); set(data, "height_px", height);
      set(data, "encoding", "rgb8"); set(data, "data", encoded);
    } else return -1;
    std::string json;
    if (!google::protobuf::util::MessageToJsonString(envelope, &json).ok() || json.size() > 12 * 1024 * 1024)
      return -1;
    return node->host->emit(node->host->context,
        reinterpret_cast<const std::uint8_t*>(json.data()), json.size());
  }
  const char* op = node->kind == "camera" ? "camera_capture" :
                   node->kind == "base" ? "base_observe" :
                   node->kind == "gripper" ? "gripper_observe" : "manipulator_observe";
  Struct reply;
  std::vector<unsigned char> payload;
  if (!exchange(node, op, &reply, &payload)) return -1;
  if (node->kind != "camera" && !payload.empty()) return -1;
  Struct envelope;
  set(&envelope, "port", node->kind == "camera" ? "frame" : "state");
  Struct* data = (*envelope.mutable_fields())["payload"].mutable_struct_value();
  const auto* time = field(reply, "timestamp_ns");
  const auto* sequence = field(reply, "sequence");
  if (!time || time->kind_case() != Value::kNumberValue ||
      !sequence || sequence->kind_case() != Value::kNumberValue) return -1;
  Struct* sample = (*data->mutable_fields())["sample"].mutable_struct_value();
  if (!std::isfinite(time->number_value()) || time->number_value() < 0 ||
      !std::isfinite(sequence->number_value()) || sequence->number_value() < 0) return -1;
  set(sample, "source_time_ns", std::round(time->number_value()));
  set(sample, "sequence", std::round(sequence->number_value()));
  set(sample, "clock", "simulation");
  set(sample, "frame_id", node->device);
  if (node->kind == "camera") {
    const auto* width = field(reply, "width_px");
    const auto* height = field(reply, "height_px");
    const auto* size = field(reply, "rgb_length");
    if (!width || !height || !size || width->kind_case() != Value::kNumberValue ||
        height->kind_case() != Value::kNumberValue || size->kind_case() != Value::kNumberValue ||
        size->number_value() != payload.size() || string_field(reply, "format") != "jpeg") return -1;
    set(data, "width_px", width->number_value());
    set(data, "height_px", height->number_value());
    set(data, "encoding", "jpeg");
    std::string encoded;
    google::protobuf::Base64Escape(
        std::string(reinterpret_cast<const char*>(payload.data()), payload.size()), &encoded);
    set(data, "data", encoded);
  } else {
    auto copy_number = [&](const char* from, const char* to) {
      const auto* value = field(reply, from);
      if (!value || value->kind_case() != Value::kNumberValue) return false;
      set(data, to, value->number_value());
      return true;
    };
    if (node->kind == "gripper") {
      const auto* opening = field(reply, "opening_percent");
      if (!opening || opening->kind_case() != Value::kNumberValue) return -1;
      auto* channel = (*data->mutable_fields())["channels"].mutable_list_value()
                          ->add_values()->mutable_struct_value();
      set(channel, "name", "opening");
      set(channel, "value", opening->number_value());
      set(channel, "unit", "%");
    } else if (node->kind == "base") {
      auto* position = field(reply, "position_m");
      auto* velocity = field(reply, "linear_velocity_m_s");
      if (!position || !velocity || position->kind_case() != Value::kListValue ||
          velocity->kind_case() != Value::kListValue ||
          position->list_value().values_size() != 2 || velocity->list_value().values_size() != 2) return -1;
      const auto& p = position->list_value().values();
      const auto& v = velocity->list_value().values();
      if (p[0].kind_case() != Value::kNumberValue || p[1].kind_case() != Value::kNumberValue ||
          v[0].kind_case() != Value::kNumberValue || v[1].kind_case() != Value::kNumberValue) return -1;
      set(data, "x_m", p[0].number_value()); set(data, "y_m", p[1].number_value());
      set(data, "vx_m_s", v[0].number_value()); set(data, "vy_m_s", v[1].number_value());
      if (!copy_number("yaw_rad", "yaw_rad") ||
          !copy_number("angular_velocity_rad_s", "yaw_rate_rad_s")) return -1;
    } else {
      const auto* positions = field(reply, "joint_positions_rad");
      const auto* velocities = field(reply, "joint_velocities_rad_s");
      if (!positions || !velocities || positions->kind_case() != Value::kListValue ||
          velocities->kind_case() != Value::kListValue ||
          positions->list_value().values_size() != 6 || velocities->list_value().values_size() != 6)
        return -1;
      static constexpr const char* names[] = {"shoulder_pan_joint", "shoulder_lift_joint",
          "elbow_joint", "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"};
      auto* joints = (*data->mutable_fields())["joint_names"].mutable_list_value();
      for (const auto* name : names) joints->add_values()->set_string_value(name);
      *(*data->mutable_fields())["position_rad"].mutable_list_value() = positions->list_value();
      *(*data->mutable_fields())["velocity_rad_s"].mutable_list_value() = velocities->list_value();
    }
  }
  std::string json;
  if (!google::protobuf::util::MessageToJsonString(envelope, &json).ok() || json.size() > 12 * 1024 * 1024)
    return -1;
  return node->host->emit(node->host->context, reinterpret_cast<const std::uint8_t*>(json.data()), json.size());
}
int32_t stop_impl(isos_node_handle* node) {
  if (!node) return -1;
  std::lock_guard lock(node->mutex);
  node->stopped = true;
  node->started = false;
  return 0;
}
void destroy_impl(isos_node_handle* node) { delete node; }
int32_t create(const std::uint8_t* config, std::size_t length,
               const isos_node_host_v1* host, isos_node_handle** out) noexcept {
  try { return create_impl(config, length, host, out); } catch (...) { return -1; }
}
int32_t start(isos_node_handle* node) noexcept {
  try { return start_impl(node); } catch (...) { return -1; }
}
int32_t health(isos_node_handle* node) noexcept {
  try { return health_impl(node); } catch (...) { return -1; }
}
int32_t input(isos_node_handle* node, const std::uint8_t* bytes, std::size_t length) noexcept {
  try { return input_impl(node, bytes, length); } catch (...) { return -1; }
}
int32_t stop(isos_node_handle* node) noexcept {
  try { return stop_impl(node); } catch (...) { return -1; }
}
void destroy(isos_node_handle* node) noexcept {
  try { destroy_impl(node); } catch (...) { }
}
const isos_node_api_v1 api{ISOS_NODE_ABI_VERSION, sizeof(isos_node_api_v1), create,
                           start, input, health, stop, destroy};
}  // namespace
extern "C" const isos_node_api_v1* isos_node_v1(void) { return &api; }

struct isos_node_v2_handle {
  const isos_node_host_v2* host = nullptr;
  isos_node_host_v1 bridge{};
  isos_node_handle* node = nullptr;
};

namespace {
int32_t bridge_emit(void* context, const std::uint8_t* bytes, std::size_t length) {
  auto* handle = static_cast<isos_node_v2_handle*>(context);
  return handle->host->emit(handle->host->context, bytes, length);
}
void bridge_log(void* context, std::uint32_t level, const std::uint8_t* bytes,
                std::size_t length) {
  auto* handle = static_cast<isos_node_v2_handle*>(context);
  if (handle->host->log) handle->host->log(handle->host->context, level, bytes, length);
}
int32_t create_v2(const std::uint8_t* config, std::size_t length,
                  const isos_node_host_v2* host, isos_node_v2_handle** out) noexcept {
  try {
    if (!host || host->abi_version != ISOS_NODE_ABI_V2 ||
        host->struct_size < sizeof(isos_node_host_v2) || !host->emit ||
        !host->stop_proof || !out) return -1;
    auto handle = std::make_unique<isos_node_v2_handle>();
    handle->host = host;
    handle->bridge = {ISOS_NODE_ABI_VERSION, sizeof(isos_node_host_v1),
                      handle.get(), bridge_emit, bridge_log};
    if (create_impl(config, length, &handle->bridge, &handle->node) != 0) return -1;
    *out = handle.release();
    return 0;
  } catch (...) { return -1; }
}
int32_t start_v2(isos_node_v2_handle* handle) noexcept {
  try { return handle ? start_impl(handle->node) : -1; } catch (...) { return -1; }
}
int32_t observe_v2(isos_node_v2_handle* handle, const std::uint8_t* bytes,
                   std::size_t length) noexcept {
  try {
    if (!handle || !handle->node) return -1;
    Struct request;
    if (bytes && length && !parse(bytes, length, &request)) return -1;
    static const std::string observation = R"({"op":"observe"})";
    return input_impl(handle->node,
        reinterpret_cast<const std::uint8_t*>(observation.data()), observation.size());
  } catch (...) { return -1; }
}
int32_t command_v2(isos_node_v2_handle* handle, const std::uint8_t* bytes,
                   std::size_t length) noexcept {
  try {
    if (!handle || !handle->node) return -1;
    auto* node = handle->node;
    std::lock_guard lock(node->mutex);
    if (!node->started || node->stopped) return -1;
    Struct admitted;
    if (!parse(bytes, length, &admitted) ||
        string_field(admitted, "command_id").empty() ||
        string_field(admitted, "run_id") != node->run_id) return -1;
    if (!node->revision.empty() && string_field(admitted, "revision") != node->revision) return -1;
    const Struct* payload = object_field(admitted, "payload");
    if (!payload) return -1;
    const char* operation = node->service_instance == "robocasa" ? "command" :
                            node->kind == "base" ? "base_move" :
                            node->kind == "manipulator" ? "manipulator_move" :
                            node->kind == "gripper" ? "gripper_move" : nullptr;
    if (!operation) return -1;
    Struct request = *payload;
    if (node->service_instance == "robocasa") {
      request.mutable_fields()->erase("values");
      if (node->kind == "manipulator" && string_field(admitted, "port") == "mode") {
        const auto* mode = field(*payload, "mode");
        if (!mode || mode->kind_case() != Value::kNumberValue ||
            (mode->number_value() != 0 && mode->number_value() != 1)) return -1;
        (*request.mutable_fields())["values"] = *mode;
        set(&request, "control_mode", "mode");
      } else if (node->kind == "gripper") {
        const auto* close = field(*payload, "close");
        if (!close || close->kind_case() != Value::kBoolValue) return -1;
        (*request.mutable_fields())["values"] = *close;
      } else {
        const Struct* axes = object_field(*payload, "axes");
        if (!axes) return -1;
        const std::vector<std::string> names = node->kind == "base"
            ? std::vector<std::string>{"x", "y", "yaw"}
            : node->kind == "torso" ? std::vector<std::string>{"lift"}
            : std::vector<std::string>{"dx", "dy", "dz", "droll", "dpitch", "dyaw"};
        if (axes->fields_size() != static_cast<int>(names.size())) return -1;
        std::vector<Value> values;
        for (const auto& name : names) {
          const auto* value = field(*axes, name.c_str());
          if (!value || value->kind_case() != Value::kNumberValue ||
              !std::isfinite(value->number_value()) || std::abs(value->number_value()) > 1) return -1;
          values.push_back(*value);
        }
        if (node->kind == "manipulator") {
          Struct* arm = (*request.mutable_fields())["values"].mutable_struct_value();
          for (int i = 0; i < 6; ++i)
            (*arm->mutable_fields())[i < 3 ? "position" : "rotation"].mutable_list_value()
                ->add_values()->CopyFrom(values[i]);
        } else {
          auto* list = (*request.mutable_fields())["values"].mutable_list_value();
          for (const auto& value : values) list->add_values()->CopyFrom(value);
        }
      }
    }
    set(&request, "command_id", string_field(admitted, "command_id"));
    set(&request, "generation_id", node->generation_id);
    const auto epoch = string_field(admitted, "stop_epoch");
    if (epoch.empty() && node->service_instance != "robocasa") return -1;
    set(&request, "stop_epoch", epoch);
    Struct reply;
    std::vector<unsigned char> binary;
    if (!exchange(node, operation, &reply, &binary, &request) || !binary.empty()) return -1;
    Struct output;
    set(&output, "port", "command_result");
    *(*output.mutable_fields())["payload"].mutable_struct_value() = reply;
    std::string json;
    if (!google::protobuf::util::MessageToJsonString(output, &json).ok() || json.size() > 65536)
      return -1;
    return handle->host->emit(handle->host->context,
        reinterpret_cast<const std::uint8_t*>(json.data()), json.size());
  } catch (...) { return -1; }
}
int32_t health_v2(isos_node_v2_handle* handle) noexcept {
  try { return handle ? health_impl(handle->node) : -1; } catch (...) { return -1; }
}
int32_t stop_v2(isos_node_v2_handle* handle, const std::uint8_t* bytes,
                std::size_t length) noexcept {
  try {
    if (!handle || !handle->node) return -1;
    auto* node = handle->node;
    std::lock_guard lock(node->mutex);
    Struct fence;
    if (!parse(bytes, length, &fence) ||
        string_field(fence, "run_id") != node->run_id) return -1;
    if (!node->revision.empty() && string_field(fence, "revision") != node->revision) return -1;
    Struct proof;
    set(&proof, "run_id", node->run_id);
    set(&proof, "revision", node->revision);
    set(&proof, "generation_id", node->generation_id);
    set(&proof, "outcome", "unknown");
    auto command_id = string_field(fence, "command_id");
    if (command_id.empty()) {
      const auto epoch = field(fence, "stop_epoch");
      if (epoch && epoch->kind_case() == Value::kNumberValue)
        command_id = node->run_id + ":stop:" + std::to_string(static_cast<std::uint64_t>(epoch->number_value()));
      else if (epoch && epoch->kind_case() == Value::kStringValue)
        command_id = node->run_id + ":stop:" + epoch->string_value();
    }
    if (node->kind != "camera" && !command_id.empty()) {
      const auto socket = node->socket;
      node->socket += ".stop";
      Struct request;
      set(&request, "command_id", command_id);
      set(&request, "generation_id", node->generation_id);
      Struct reply;
      std::vector<unsigned char> binary;
      const bool success = exchange(node, "stop", &reply, &binary, &request) && binary.empty() &&
          string_field(reply, "base_stop") == "stopped" &&
          string_field(reply, "arm_stop") == "stopped" &&
          string_field(reply, "gripper_stop") == "stopped" &&
          (node->service_instance != "robocasa" ||
           string_field(reply, "torso_stop") == "stopped");
      node->socket = socket;
      if (success) set(&proof, "outcome", "stopped");
      set(&proof, "base_stop", string_field(reply, "base_stop"));
      set(&proof, "arm_stop", string_field(reply, "arm_stop"));
      set(&proof, "gripper_stop", string_field(reply, "gripper_stop"));
      if (node->service_instance == "robocasa")
        set(&proof, "torso_stop", string_field(reply, "torso_stop"));
      Struct* actuators = (*proof.mutable_fields())["actuators"].mutable_struct_value();
      set(actuators, "base", string_field(reply, "base_stop"));
      set(actuators, "manipulator", string_field(reply, "arm_stop"));
      set(actuators, "gripper", string_field(reply, "gripper_stop"));
      if (node->service_instance == "robocasa")
        set(actuators, "torso", string_field(reply, "torso_stop"));
      set(&proof, "stop_epoch", string_field(reply, "stop_epoch"));
    } else if (node->kind == "camera") {
      set(&proof, "outcome", "stopped");
    }
    node->stopped = true;
    node->started = false;
    std::string json;
    if (!google::protobuf::util::MessageToJsonString(proof, &json).ok() || json.size() > 16384)
      return -1;
    const auto emitted = handle->host->stop_proof(handle->host->context,
        reinterpret_cast<const std::uint8_t*>(json.data()), json.size());
    return emitted == 0 && string_field(proof, "outcome") == "stopped" ? 0 : -1;
  } catch (...) { return -1; }
}
void destroy_v2(isos_node_v2_handle* handle) noexcept {
  try {
    if (!handle) return;
    delete handle->node;
    delete handle;
  } catch (...) { }
}
const isos_node_api_v2 api_v2{ISOS_NODE_ABI_V2, sizeof(isos_node_api_v2), create_v2,
                              start_v2, observe_v2, command_v2, health_v2, stop_v2, destroy_v2};
}  // namespace
extern "C" const isos_node_api_v2* isos_node_v2(void) { return &api_v2; }
