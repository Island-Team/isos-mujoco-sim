#include <google/protobuf/struct.pb.h>
#include <google/protobuf/stubs/strutil.h>
#include <google/protobuf/util/json_util.h>
#include <jpeglib.h>
#include <poll.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include <array>
#include <cerrno>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_set>
#include <vector>

#include "isos_node_v1.h"
#include "isos_node_v2.h"

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
  std::string manifest_digest;
  bool legacy_contract = false;
  Struct profile;
  bool started = false;
  bool stopped = false;
  std::uint64_t request = 0;
  std::uint64_t frame_sequence = 0;
};

namespace {
std::vector<unsigned char> encode_jpeg(const std::vector<unsigned char>& rgb, int width,
                                       int height) {
  jpeg_compress_struct jpeg{};
  jpeg_error_mgr error{};
  jpeg.err = jpeg_std_error(&error);
  jpeg_create_compress(&jpeg);
  unsigned char* output = nullptr;
  unsigned long output_size = 0;
  jpeg_mem_dest(&jpeg, &output, &output_size);
  jpeg.image_width = width;
  jpeg.image_height = height;
  jpeg.input_components = 3;
  jpeg.in_color_space = JCS_RGB;
  jpeg_set_defaults(&jpeg);
  jpeg_set_quality(&jpeg, 80, TRUE);
  jpeg_start_compress(&jpeg, TRUE);
  while (jpeg.next_scanline < jpeg.image_height) {
    JSAMPROW row =
        const_cast<JSAMPROW>(rgb.data() + static_cast<std::size_t>(jpeg.next_scanline) * width * 3);
    jpeg_write_scanlines(&jpeg, &row, 1);
  }
  jpeg_finish_compress(&jpeg);
  std::vector<unsigned char> encoded(output, output + output_size);
  jpeg_destroy_compress(&jpeg);
  std::free(output);
  return encoded;
}
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
    if (errno != EINPROGRESS) {
      ::close(fd);
      return false;
    }
    pollfd event{fd, POLLOUT, 0};
    int error = 0;
    socklen_t size = sizeof(error);
    if (::poll(&event, 1, 1000) <= 0 ||
        ::getsockopt(fd, SOL_SOCKET, SO_ERROR, &error, &size) != 0 || error) {
      ::close(fd);
      return false;
    }
  }
  std::array<unsigned char, 8> header{};
  encode(&header, static_cast<std::uint32_t>(json.size()));
  bool ok = write_exact(fd, header.data(), header.size()) &&
            write_exact(fd, json.data(), json.size()) &&
            read_exact(fd, header.data(), header.size());
  if (!ok) {
    ::close(fd);
    return false;
  }
  const auto meta_size = decode(header, 0);
  const auto payload_size = decode(header, 4);
  if (meta_size == 0 || meta_size > 65536 || payload_size > 12582912) {
    ::close(fd);
    return false;
  }
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
      string_field(reply, "version") != "2.0.0")
    return false;
  auto* accepted = field(reply, "accepted");
  auto* features = field(reply, "features");
  if (!accepted || accepted->kind_case() != Value::kBoolValue || !accepted->bool_value() ||
      !features || features->kind_case() != Value::kListValue)
    return false;
  if (!node->manifest_digest.empty() &&
      string_field(reply, "manifest_digest") != node->manifest_digest)
    return false;
  const auto generation = string_field(reply, "generation_id");
  if (!generation.empty()) {
    if (!node->generation_id.empty() && node->generation_id != generation) return false;
    node->generation_id = generation;
  }
  for (const auto& item : features->list_value().values())
    if (item.kind_case() == Value::kStringValue && item.string_value() == "strict-socket-v1")
      return true;
  return false;
}
int32_t create_impl(const std::uint8_t* config, std::size_t length, const isos_node_host_v1* host,
                    isos_node_handle** out) {
  if (!host || host->abi_version != ISOS_NODE_ABI_VERSION ||
      host->struct_size < sizeof(isos_node_host_v1) || !host->emit || !out)
    return -1;
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
  node->profile = *instance;
  if (const auto* package = object_field(*instance, "package")) {
    const auto version = string_field(*package, "version");
    node->legacy_contract = version == "0.2.0" || version == "0.2.1" || version == "0.2.2" ||
                            version == "0.2.3" || version == "0.2.4" || version == "0.2.5" ||
                            version == "0.2.6" || version == "0.2.7";
  }
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
  node->manifest_digest = string_field(*settings, "robot_manifest_digest");
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
  // Protobuf Struct numbers must preserve the stream counter exactly as JSON integers.
  if (node->kind == "camera" && node->frame_sequence >= 9007199254740991ULL) return -1;
  Struct request;
  if (!parse(bytes, length, &request) || string_field(request, "op") != "observe") return -1;
  if (node->service_instance == "robocasa") {
    Struct reply;
    std::vector<unsigned char> binary;
    if (!exchange(node, "observe", &reply, &binary)) return -1;
    const Struct* values = object_field(reply, "values");
    const auto* sequence = field(reply, "sequence");
    const auto* timestamp = field(reply, "timestamp_ns");
    if ((!values && node->kind != "camera") || !sequence || !timestamp ||
        sequence->kind_case() != Value::kNumberValue ||
        timestamp->kind_case() != Value::kNumberValue)
      return -1;
    if (node->kind != "camera" && !binary.empty()) return -1;
    Struct envelope;
    set(&envelope, "port",
        node->kind == "camera"  ? "frame"
        : node->legacy_contract ? "state"
                                : "observation");
    Struct* data = (*envelope.mutable_fields())["payload"].mutable_struct_value();
    Struct* sample = (*data->mutable_fields())["sample"].mutable_struct_value();
    if (!std::isfinite(timestamp->number_value()) || timestamp->number_value() < 0 ||
        !std::isfinite(sequence->number_value()) || sequence->number_value() < 0)
      return -1;
    set(sample, "source_time_ns", std::round(timestamp->number_value()));
    set(sample, "sequence",
        node->kind == "camera" ? static_cast<double>(node->frame_sequence + 1)
                               : std::round(sequence->number_value()));
    set(sample, "clock", "monotonic");
    set(sample, "frame_id",
        !string_field(node->profile, "frame_id").empty() ? string_field(node->profile, "frame_id")
        : node->kind == "base"                           ? "world"
        : node->kind == "manipulator"                    ? "robot_base"
                                                         : node->device);
    if (node->kind == "base" || node->kind == "manipulator") {
      const char* position_key =
          node->kind == "base" ? "base_position" : "end_effector_position_relative";
      const char* rotation_key =
          node->kind == "base" ? "base_rotation" : "end_effector_rotation_relative";
      const auto* position = field(*values, position_key);
      const auto* rotation = field(*values, rotation_key);
      if (!position || !rotation || position->kind_case() != Value::kListValue ||
          rotation->kind_case() != Value::kListValue || position->list_value().values_size() != 3 ||
          rotation->list_value().values_size() != 4)
        return -1;
      double norm = 0;
      for (const auto& element : position->list_value().values())
        if (element.kind_case() != Value::kNumberValue || !std::isfinite(element.number_value()))
          return -1;
      for (const auto& element : rotation->list_value().values()) {
        if (element.kind_case() != Value::kNumberValue || !std::isfinite(element.number_value()))
          return -1;
        norm += element.number_value() * element.number_value();
      }
      if (std::abs(norm - 1.0) > 0.02) return -1;
      *(*data->mutable_fields())["position_m"].mutable_list_value() = position->list_value();
      *(*data->mutable_fields())["orientation_xyzw"].mutable_list_value() = rotation->list_value();
    } else if (node->kind == "gripper" || node->kind == "torso") {
      const auto* channels = field(reply, "channels");
      if (channels && channels->kind_case() == Value::kListValue) {
        if (channels->list_value().values_size() < 1 ||
            channels->list_value().values_size() > (node->kind == "gripper" ? 32 : 64))
          return -1;
        std::unordered_set<std::string> names;
        for (const auto& value : channels->list_value().values()) {
          if (value.kind_case() != Value::kStructValue) return -1;
          const auto& item = value.struct_value();
          const auto name = string_field(item, "name");
          const auto unit = string_field(item, "unit");
          const auto* scalar = field(item, "value");
          if (name.empty() || name.size() > 64 || !names.insert(name).second ||
              (unit != "m" && unit != "rad") || !scalar ||
              scalar->kind_case() != Value::kNumberValue || !std::isfinite(scalar->number_value()))
            return -1;
        }
        *(*data->mutable_fields())["channels"].mutable_list_value() = channels->list_value();
      } else if (node->kind == "gripper") {
        // Legacy private worker replies retain the fixed Panda finger channels.
        const auto* positions = field(*values, "gripper_qpos");
        if (!positions || positions->kind_case() != Value::kListValue ||
            positions->list_value().values_size() != 2)
          return -1;
        auto* output = (*data->mutable_fields())["channels"].mutable_list_value();
        for (int i = 0; i < 2; ++i) {
          const auto& value = positions->list_value().values(i);
          if (value.kind_case() != Value::kNumberValue || !std::isfinite(value.number_value()))
            return -1;
          Struct* channel = output->add_values()->mutable_struct_value();
          set(channel, "name", i == 0 ? "left_finger" : "right_finger");
          set(channel, "value", value.number_value());
          set(channel, "unit", "m");
        }
      } else
        return -1;
    } else if (node->kind == "camera") {
      const auto* width_value = field(reply, "width_px");
      const auto* height_value = field(reply, "height_px");
      if (!width_value || !height_value || width_value->kind_case() != Value::kNumberValue ||
          height_value->kind_case() != Value::kNumberValue)
        return -1;
      const double width_number = width_value->number_value();
      const double height_number = height_value->number_value();
      if (std::floor(width_number) != width_number || std::floor(height_number) != height_number ||
          width_number < 64 || width_number > 2048 || height_number < 64 || height_number > 2048)
        return -1;
      const int width = static_cast<int>(width_number);
      const int height = static_cast<int>(height_number);
      if (binary.size() != static_cast<std::size_t>(width) * height * 3) return -1;
      const auto jpeg = encode_jpeg(binary, width, height);
      if (jpeg.empty() || jpeg.size() > 8 * 1024 * 1024) return -1;
      std::string encoded;
      google::protobuf::Base64Escape(
          std::string(reinterpret_cast<const char*>(jpeg.data()), jpeg.size()), &encoded);
      set(data, "width_px", width);
      set(data, "height_px", height);
      set(data, "encoding", "jpeg");
      set(data, "data", encoded);
    } else
      return -1;
    std::string json;
    if (!google::protobuf::util::MessageToJsonString(envelope, &json).ok() ||
        json.size() > 20 * 1024 * 1024)
      return -1;
    const auto emitted = node->host->emit(
        node->host->context, reinterpret_cast<const std::uint8_t*>(json.data()), json.size());
    if (emitted == 0 && node->kind == "camera") ++node->frame_sequence;
    return emitted;
  }
  const char* op = node->kind == "camera"    ? "camera_capture"
                   : node->kind == "base"    ? "base_observe"
                   : node->kind == "gripper" ? "gripper_observe"
                                             : "manipulator_observe";
  Struct reply;
  std::vector<unsigned char> payload;
  if (!exchange(node, op, &reply, &payload)) return -1;
  if (node->kind != "camera" && !payload.empty()) return -1;
  Struct envelope;
  set(&envelope, "port",
      node->kind == "camera"  ? "frame"
      : node->legacy_contract ? "state"
                              : "observation");
  Struct* data = (*envelope.mutable_fields())["payload"].mutable_struct_value();
  const auto* time = field(reply, "timestamp_ns");
  const auto* sequence = field(reply, "sequence");
  if (!time || time->kind_case() != Value::kNumberValue || !sequence ||
      sequence->kind_case() != Value::kNumberValue)
    return -1;
  Struct* sample = (*data->mutable_fields())["sample"].mutable_struct_value();
  if (!std::isfinite(time->number_value()) || time->number_value() < 0 ||
      !std::isfinite(sequence->number_value()) || sequence->number_value() < 0)
    return -1;
  set(sample, "source_time_ns", std::round(time->number_value()));
  set(sample, "sequence",
      node->kind == "camera" ? static_cast<double>(node->frame_sequence + 1)
                             : std::round(sequence->number_value()));
  set(sample, "clock", "simulation");
  set(sample, "frame_id",
      node->legacy_contract         ? node->device
      : node->kind == "base"        ? "world"
      : node->kind == "manipulator" ? string_field(node->profile, "frame_id")
                                    : node->device);
  if (node->kind == "camera") {
    const auto* width = field(reply, "width_px");
    const auto* height = field(reply, "height_px");
    const auto* size = field(reply, "rgb_length");
    if (!width || !height || !size || width->kind_case() != Value::kNumberValue ||
        height->kind_case() != Value::kNumberValue || size->kind_case() != Value::kNumberValue ||
        size->number_value() != payload.size() || string_field(reply, "format") != "jpeg")
      return -1;
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
      auto* channel = (*data->mutable_fields())["channels"]
                          .mutable_list_value()
                          ->add_values()
                          ->mutable_struct_value();
      set(channel, "name", "opening");
      set(channel, "value", opening->number_value());
      set(channel, "unit", "%");
    } else if (node->kind == "base") {
      auto* position = field(reply, "position_m");
      auto* velocity = field(reply, "linear_velocity_m_s");
      if (!position || !velocity || position->kind_case() != Value::kListValue ||
          velocity->kind_case() != Value::kListValue || position->list_value().values_size() != 2 ||
          velocity->list_value().values_size() != 2)
        return -1;
      const auto& p = position->list_value().values();
      const auto& v = velocity->list_value().values();
      if (p[0].kind_case() != Value::kNumberValue || p[1].kind_case() != Value::kNumberValue ||
          v[0].kind_case() != Value::kNumberValue || v[1].kind_case() != Value::kNumberValue)
        return -1;
      set(data, "x_m", p[0].number_value());
      set(data, "y_m", p[1].number_value());
      set(data, "vx_m_s", v[0].number_value());
      set(data, "vy_m_s", v[1].number_value());
      if (!copy_number("yaw_rad", "yaw_rad") ||
          !copy_number("angular_velocity_rad_s", "yaw_rate_rad_s"))
        return -1;
    } else {
      const auto* positions = field(reply, "joint_positions_rad");
      const auto* velocities = field(reply, "joint_velocities_rad_s");
      if (!positions || !velocities || positions->kind_case() != Value::kListValue ||
          velocities->kind_case() != Value::kListValue ||
          positions->list_value().values_size() != 6 || velocities->list_value().values_size() != 6)
        return -1;
      static constexpr const char* names[] = {"shoulder_pan_joint", "shoulder_lift_joint",
                                              "elbow_joint",        "wrist_1_joint",
                                              "wrist_2_joint",      "wrist_3_joint"};
      auto* joints = (*data->mutable_fields())["joint_names"].mutable_list_value();
      for (const auto* name : names) joints->add_values()->set_string_value(name);
      *(*data->mutable_fields())["position_rad"].mutable_list_value() = positions->list_value();
      *(*data->mutable_fields())["velocity_rad_s"].mutable_list_value() = velocities->list_value();
    }
  }
  std::string json;
  if (!google::protobuf::util::MessageToJsonString(envelope, &json).ok() ||
      json.size() > 20 * 1024 * 1024)
    return -1;
  const auto emitted = node->host->emit(
      node->host->context, reinterpret_cast<const std::uint8_t*>(json.data()), json.size());
  if (emitted == 0 && node->kind == "camera") ++node->frame_sequence;
  return emitted;
}
int32_t stop_impl(isos_node_handle* node) {
  if (!node) return -1;
  std::lock_guard lock(node->mutex);
  node->stopped = true;
  node->started = false;
  return 0;
}
void destroy_impl(isos_node_handle* node) { delete node; }
int32_t create(const std::uint8_t* config, std::size_t length, const isos_node_host_v1* host,
               isos_node_handle** out) noexcept {
  try {
    return create_impl(config, length, host, out);
  } catch (...) {
    return -1;
  }
}
int32_t start(isos_node_handle* node) noexcept {
  try {
    return start_impl(node);
  } catch (...) {
    return -1;
  }
}
int32_t health(isos_node_handle* node) noexcept {
  try {
    return health_impl(node);
  } catch (...) {
    return -1;
  }
}
int32_t input(isos_node_handle* node, const std::uint8_t* bytes, std::size_t length) noexcept {
  try {
    return input_impl(node, bytes, length);
  } catch (...) {
    return -1;
  }
}
int32_t stop(isos_node_handle* node) noexcept {
  try {
    return stop_impl(node);
  } catch (...) {
    return -1;
  }
}
void destroy(isos_node_handle* node) noexcept {
  try {
    destroy_impl(node);
  } catch (...) {
  }
}
const isos_node_api_v1 api{
    ISOS_NODE_ABI_VERSION, sizeof(isos_node_api_v1), create, start, input, health, stop, destroy};
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
void bridge_log(void* context, std::uint32_t level, const std::uint8_t* bytes, std::size_t length) {
  auto* handle = static_cast<isos_node_v2_handle*>(context);
  if (handle->host->log) handle->host->log(handle->host->context, level, bytes, length);
}
int32_t create_v2(const std::uint8_t* config, std::size_t length, const isos_node_host_v2* host,
                  isos_node_v2_handle** out) noexcept {
  try {
    if (!host || host->abi_version != ISOS_NODE_ABI_V2 ||
        host->struct_size < sizeof(isos_node_host_v2) || !host->emit || !host->stop_proof || !out)
      return -1;
    auto handle = std::make_unique<isos_node_v2_handle>();
    handle->host = host;
    handle->bridge = {ISOS_NODE_ABI_VERSION, sizeof(isos_node_host_v1), handle.get(), bridge_emit,
                      bridge_log};
    if (create_impl(config, length, &handle->bridge, &handle->node) != 0) return -1;
    *out = handle.release();
    return 0;
  } catch (...) {
    return -1;
  }
}
int32_t start_v2(isos_node_v2_handle* handle) noexcept {
  try {
    return handle ? start_impl(handle->node) : -1;
  } catch (...) {
    return -1;
  }
}
int32_t observe_v2(isos_node_v2_handle* handle, const std::uint8_t* bytes,
                   std::size_t length) noexcept {
  try {
    if (!handle || !handle->node) return -1;
    Struct request;
    if (bytes && length && !parse(bytes, length, &request)) return -1;
    static const std::string observation = R"({"op":"observe"})";
    return input_impl(handle->node, reinterpret_cast<const std::uint8_t*>(observation.data()),
                      observation.size());
  } catch (...) {
    return -1;
  }
}
bool exact_fields(const Struct& object, const std::vector<std::string>& names) {
  if (object.fields_size() != static_cast<int>(names.size())) return false;
  for (const auto& name : names)
    if (!field(object, name.c_str())) return false;
  return true;
}
bool number(const Struct& object, const char* name, double* result) {
  const auto* value = field(object, name);
  if (!value || value->kind_case() != Value::kNumberValue || !std::isfinite(value->number_value()))
    return false;
  *result = value->number_value();
  return true;
}
bool standard_command(isos_node_handle* node, const Struct& payload, bool mode, Struct* request) {
  const bool robocasa = node->service_instance == "robocasa";
  if (mode) {
    const auto value = string_field(payload, "mode");
    if (!exact_fields(payload, {"mode"}) || (value != "0" && value != "1")) return false;
    set(request, "values", value == "1" ? 1.0 : 0.0);
    set(request, "control_mode", "mode");
    return true;
  }
  if (node->kind == "gripper") {
    const auto action = string_field(payload, "action");
    if (!exact_fields(payload, {"action"}) || (action != "open" && action != "close")) return false;
    (*request->mutable_fields())[robocasa ? "values" : "close"].set_bool_value(action == "close");
    return true;
  }
  const auto* movement = object_field(node->profile, "movement");
  const auto* limits = movement ? object_field(*movement, "limits") : nullptr;
  if (!limits) return false;
  auto bounded = [&](const char* key, double value) {
    double maximum;
    return number(*limits, key, &maximum) && maximum > 0 && std::abs(value) <= maximum;
  };
  auto lease_valid = [&]() {
    double lease;
    return number(payload, "lease_ms", &lease) && lease >= 1 && lease <= 1000 &&
           std::floor(lease) == lease && bounded("max_velocity_lease_ms", lease);
  };
  if (robocasa) {
    if (!exact_fields(payload, {"axes", "lease_ms"}) || !lease_valid()) return false;
    (*request->mutable_fields())["lease_ms"] = *field(payload, "lease_ms");
    const auto* axes = object_field(payload, "axes");
    const std::vector<std::string> names =
        node->kind == "base" ? std::vector<std::string>{"x", "y", "yaw"}
        : node->kind == "torso"
            ? std::vector<std::string>{"lift"}
            : std::vector<std::string>{"dx", "dy", "dz", "droll", "dpitch", "dyaw"};
    if (!axes || !exact_fields(*axes, names)) return false;
    for (std::size_t i = 0; i < names.size(); ++i) {
      double value;
      if (!number(*axes, names[i].c_str(), &value) || std::abs(value) > 1) return false;
      if (node->kind == "manipulator") {
        auto* arm = (*request->mutable_fields())["values"].mutable_struct_value();
        (*arm->mutable_fields())[i < 3 ? "position" : "rotation"]
            .mutable_list_value()
            ->add_values()
            ->set_number_value(value);
      } else {
        (*request->mutable_fields())["values"].mutable_list_value()->add_values()->set_number_value(
            value);
      }
    }
    return true;
  }
  if (node->kind == "base") {
    if (!exact_fields(payload, {"frame_id", "vx_m_s", "vy_m_s", "yaw_rate_rad_s", "lease_ms"}) ||
        !lease_valid() || string_field(payload, "frame_id").empty() ||
        string_field(payload, "frame_id") != string_field(node->profile, "frame_id"))
      return false;
    double x, y, yaw;
    if (!number(payload, "vx_m_s", &x) || !number(payload, "vy_m_s", &y) ||
        !number(payload, "yaw_rate_rad_s", &yaw) || !bounded("max_linear_m_s", std::hypot(x, y)) ||
        !bounded("max_angular_rad_s", yaw))
      return false;
    set(request, "linear_x_m_s", x);
    set(request, "linear_y_m_s", y);
    set(request, "angular_z_rad_s", yaw);
    (*request->mutable_fields())["valid_for_ms"] = *field(payload, "lease_ms");
    return true;
  }
  if (node->kind == "manipulator") {
    if (!exact_fields(payload, {"joint_names", "position_rad"})) return false;
    const auto* names = field(payload, "joint_names");
    const auto* selected = field(node->profile, "joint_names");
    const auto* positions = field(payload, "position_rad");
    if (!names || !selected || !positions || names->kind_case() != Value::kListValue ||
        selected->kind_case() != Value::kListValue || positions->kind_case() != Value::kListValue ||
        names->list_value().values_size() != 6 || selected->list_value().values_size() != 6 ||
        positions->list_value().values_size() != 6)
      return false;
    for (int i = 0; i < 6; ++i) {
      const auto& name = names->list_value().values(i);
      const auto& expected = selected->list_value().values(i);
      const auto& value = positions->list_value().values(i);
      if (name.kind_case() != Value::kStringValue || expected.kind_case() != Value::kStringValue ||
          name.string_value().empty() || name.string_value() != expected.string_value() ||
          value.kind_case() != Value::kNumberValue || !std::isfinite(value.number_value()) ||
          !bounded("max_joint_position_rad", value.number_value()))
        return false;
    }
    (*request->mutable_fields())["joint_positions_rad"] = *positions;
    return true;
  }
  return false;
}
int32_t command_v2(isos_node_v2_handle* handle, const std::uint8_t* bytes,
                   std::size_t length) noexcept {
  try {
    if (!handle || !handle->node) return -1;
    auto* node = handle->node;
    std::lock_guard lock(node->mutex);
    if (!node->started || node->stopped) return -1;
    Struct admitted;
    if (!parse(bytes, length, &admitted) || string_field(admitted, "command_id").empty() ||
        string_field(admitted, "run_id") != node->run_id)
      return -1;
    if (!node->revision.empty() && string_field(admitted, "revision") != node->revision) return -1;
    const Struct* payload = object_field(admitted, "payload");
    if (!payload) return -1;
    const char* operation = node->service_instance == "robocasa" ? "command"
                            : node->kind == "base"               ? "base_move"
                            : node->kind == "manipulator"        ? "manipulator_move"
                            : node->kind == "gripper"            ? "gripper_move"
                                                                 : nullptr;
    if (!operation) return -1;
    Struct request;
    auto copy_required = [&](const char* name) {
      const auto* value = field(*payload, name);
      if (!value) return false;
      (*request.mutable_fields())[name] = *value;
      return true;
    };
    const auto port = string_field(admitted, "port");
    const bool mode_command =
        node->service_instance == "robocasa" && node->kind == "manipulator" && port == "mode";
    if (!port.empty() && port != "command" && !mode_command) return -1;
    if (!node->legacy_contract) {
      if (!standard_command(node, *payload, mode_command, &request)) return -1;
    } else if (node->service_instance == "robocasa") {
      if (mode_command) {
        const auto* mode = field(*payload, "mode");
        if (!mode || mode->kind_case() != Value::kNumberValue ||
            (mode->number_value() != 0 && mode->number_value() != 1))
          return -1;
        (*request.mutable_fields())["values"] = *mode;
        set(&request, "control_mode", "mode");
      } else if (node->kind == "gripper") {
        const auto* close = field(*payload, "close");
        if (!close || close->kind_case() != Value::kBoolValue) return -1;
        (*request.mutable_fields())["values"] = *close;
      } else {
        const Struct* axes = object_field(*payload, "axes");
        if (!axes) return -1;
        const std::vector<std::string> names =
            node->kind == "base" ? std::vector<std::string>{"x", "y", "yaw"}
            : node->kind == "torso"
                ? std::vector<std::string>{"lift"}
                : std::vector<std::string>{"dx", "dy", "dz", "droll", "dpitch", "dyaw"};
        std::vector<Value> values;
        for (const auto& name : names) {
          const auto* value = field(*axes, name.c_str());
          if (!value || value->kind_case() != Value::kNumberValue ||
              !std::isfinite(value->number_value()) || std::abs(value->number_value()) > 1)
            return -1;
          values.push_back(*value);
        }
        if (node->kind == "manipulator") {
          Struct* arm = (*request.mutable_fields())["values"].mutable_struct_value();
          for (int i = 0; i < 6; ++i)
            (*arm->mutable_fields())[i < 3 ? "position" : "rotation"]
                .mutable_list_value()
                ->add_values()
                ->CopyFrom(values[i]);
        } else {
          auto* list = (*request.mutable_fields())["values"].mutable_list_value();
          for (const auto& value : values) list->add_values()->CopyFrom(value);
        }
      }
    } else {
      const std::vector<const char*> names =
          node->kind == "base" ? std::vector<const char*>{"linear_x_m_s", "linear_y_m_s",
                                                          "angular_z_rad_s", "valid_for_ms"}
          : node->kind == "manipulator" ? std::vector<const char*>{"joint_positions_rad"}
                                        : std::vector<const char*>{"close"};
      for (const auto* name : names)
        if (!copy_required(name)) return -1;
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
  } catch (...) {
    return -1;
  }
}
int32_t health_v2(isos_node_v2_handle* handle) noexcept {
  try {
    return handle ? health_impl(handle->node) : -1;
  } catch (...) {
    return -1;
  }
}
int32_t stop_v2(isos_node_v2_handle* handle, const std::uint8_t* bytes,
                std::size_t length) noexcept {
  try {
    if (!handle || !handle->node) return -1;
    auto* node = handle->node;
    std::lock_guard lock(node->mutex);
    Struct fence;
    if (!parse(bytes, length, &fence) || string_field(fence, "run_id") != node->run_id) return -1;
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
        command_id = node->run_id +
                     ":stop:" + std::to_string(static_cast<std::uint64_t>(epoch->number_value()));
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
      const bool success =
          exchange(node, "stop", &reply, &binary, &request) && binary.empty() &&
          string_field(reply, "base_stop") == "stopped" &&
          string_field(reply, "arm_stop") == "stopped" &&
          string_field(reply, "gripper_stop") == "stopped" &&
          (node->service_instance != "robocasa" || string_field(reply, "torso_stop") == "stopped");
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
    const auto emitted = handle->host->stop_proof(
        handle->host->context, reinterpret_cast<const std::uint8_t*>(json.data()), json.size());
    return emitted == 0 && string_field(proof, "outcome") == "stopped" ? 0 : -1;
  } catch (...) {
    return -1;
  }
}
void destroy_v2(isos_node_v2_handle* handle) noexcept {
  try {
    if (!handle) return;
    delete handle->node;
    delete handle;
  } catch (...) {
  }
}
const isos_node_api_v2 api_v2{ISOS_NODE_ABI_V2, sizeof(isos_node_api_v2),
                              create_v2,        start_v2,
                              observe_v2,       command_v2,
                              health_v2,        stop_v2,
                              destroy_v2};
}  // namespace
extern "C" const isos_node_api_v2* isos_node_v2(void) { return &api_v2; }
