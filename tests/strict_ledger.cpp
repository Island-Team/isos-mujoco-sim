#include "strict_ledger.h"

#include <cassert>
#include <iostream>

int main() {
  using eos_mujoco::StrictLedger;
  StrictLedger ledger;
  auto first = ledger.Reserve("base-0", "uncertain-1", false, "base_move:0.2");
  assert(first.admission == StrictLedger::Admission::New);
  assert(ledger.Reserve("base-0", "uncertain-1", false, "base_move:0.2").admission ==
         StrictLedger::Admission::InProgress);
  ledger.Finish("base-0", "uncertain-1", false, false, "device_unavailable",
                "movement outcome uncertain", 1234, 56);
  const auto replay = ledger.Reserve("base-0", "uncertain-1", false, "base_move:0.2");
  assert(replay.admission == StrictLedger::Admission::Prior);
  assert(!replay.result.accepted && replay.result.complete);
  assert(replay.result.error_message == "movement outcome uncertain");
  assert(replay.result.timestamp_ns == 1234 && replay.result.sequence == 56);
  assert(ledger.Reserve("base-0", "uncertain-1", false, "base_move:0.3").admission ==
         StrictLedger::Admission::Conflict);
  assert(ledger.Reserve("base-0", "uncertain-1", true, "stop").admission ==
         StrictLedger::Admission::Conflict);
  assert(ledger.Reserve("arm-0", "uncertain-1", false, "arm_move:0.2").admission ==
         StrictLedger::Admission::New);
  assert(ledger.Reserve("base-0", "late", false, "base_move:epoch=0", false).admission ==
         StrictLedger::Admission::Stale);
  assert(ledger.Reserve("base-0", "late", false, "base_move:epoch=1").admission ==
         StrictLedger::Admission::New);
  ledger.Finish("base-0", "late", false, true, "", "", 2000, 57);
  assert(ledger.Reserve("base-0", "late", false, "base_move:epoch=1", false).admission ==
         StrictLedger::Admission::Prior);
  assert(ledger.Reserve("base-0", "late", false, "base_move:epoch=2").admission ==
         StrictLedger::Admission::Conflict);
  assert(ledger.Reserve("base-0", "stop-1", true, "stop").admission ==
         StrictLedger::Admission::New);
  ledger.Finish("base-0", "stop-1", true, true, "", "", 3000, 58, "stopped", "stopped", "1");
  const auto stop = ledger.Reserve("base-0", "stop-1", true, "stop");
  assert(stop.admission == StrictLedger::Admission::Prior);
  assert(ledger.Reserve("base-0", "stop-1", true, "stop", true, false).admission ==
         StrictLedger::Admission::Prior);
  assert(ledger.Reserve("base-0", "stop-2", true, "stop", true, false).admission ==
         StrictLedger::Admission::Capacity);
  assert(stop.result.base_stop == "stopped" && stop.result.arm_stop == "stopped" &&
         stop.result.stop_epoch == "1");
  std::cout << "uncertain released identity remains retained for this generation\n";
}
