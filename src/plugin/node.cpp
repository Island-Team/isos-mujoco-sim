#include "isos_node_v1.h"

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
              std::vector<unsigned char>* payload) {
  if (node->socket.empty() || node->socket.size() >= sizeof(sockaddr_un::sun_path)) return false;
  Struct request;
  set(&request, "version", "2.0.0");
  set(&request, "id", "plugin-" + std::to_string(++node->request));
  set(&request, "node", node->device);
  set(&request, "op", op);
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
  node->device = string_field(*settings, "simulator_node");
  if (node->device.empty()) node->device = string_field(*settings, "device_id");
  const auto type = string_field(*instance, "node_type");
  if (type == "eos.hardware.camera.device@v0.2") node->kind = "camera";
  if (type == "eos.hardware.base.device@v0.2") node->kind = "base";
  if (type == "eos.hardware.manipulator.device@v0.2") node->kind = "manipulator";
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
  const char* op = node->kind == "camera" ? "camera_capture" :
                   node->kind == "base" ? "base_observe" : "manipulator_observe";
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
  set(sample, "source_time_ns", time->number_value());
  set(sample, "sequence", sequence->number_value());
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
    if (node->kind == "base") {
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
      static constexpr const char* names[] = {"joint1", "joint2", "joint3", "joint4", "joint5", "joint6"};
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
