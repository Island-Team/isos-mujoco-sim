#pragma once

#include <cstdint>
#include <map>
#include <string>
#include <utility>

namespace eos_mujoco {

// Process-generation command retention. No entry is evicted or reused.
class StrictLedger {
 public:
  struct Result {
    bool complete = false;
    bool accepted = false;
    std::string error_code;
    std::string error_message;
    double timestamp_ns = 0;
    std::uint64_t sequence = 0;
    std::string base_stop, arm_stop, stop_epoch;
  };
  enum class Admission { New, Prior, Conflict, InProgress, Capacity, Stale };
  struct Reservation {
    Admission admission;
    Result result;
  };

  Reservation Reserve(const std::string& node, const std::string& command_id, bool stop,
                      const std::string& fingerprint, bool epoch_current = true) {
    const Key key{node, command_id};
    auto& table = stop ? stops_ : movements_;
    const auto& other = stop ? movements_ : stops_;
    if (other.contains(key)) return {Admission::Conflict, {}};
    const auto found = table.find(key);
    if (found != table.end()) {
      if (found->second.fingerprint != fingerprint) return {Admission::Conflict, {}};
      return {found->second.result.complete ? Admission::Prior : Admission::InProgress,
              found->second.result};
    }
    if (!stop && !epoch_current) return {Admission::Stale, {}};
    if (table.size() >= (stop ? 4096u : 65536u)) return {Admission::Capacity, {}};
    table.emplace(key, Entry{fingerprint, {}});
    return {Admission::New, {}};
  }

  void Finish(const std::string& node, const std::string& command_id, bool stop, bool accepted,
              std::string error_code, std::string error_message, double timestamp_ns,
              std::uint64_t sequence, std::string base_stop = {}, std::string arm_stop = {},
              std::string stop_epoch = {}) {
    auto& table = stop ? stops_ : movements_;
    auto& result = table.at(Key{node, command_id}).result;
    result.accepted = accepted;
    result.error_code = std::move(error_code);
    result.error_message = std::move(error_message);
    result.timestamp_ns = timestamp_ns;
    result.sequence = sequence;
    result.base_stop = std::move(base_stop);
    result.arm_stop = std::move(arm_stop);
    result.stop_epoch = std::move(stop_epoch);
    result.complete = true;
  }

 private:
  using Key = std::pair<std::string, std::string>;
  struct Entry {
    std::string fingerprint;
    Result result;
  };
  std::map<Key, Entry> movements_;
  std::map<Key, Entry> stops_;
};

}  // namespace eos_mujoco
