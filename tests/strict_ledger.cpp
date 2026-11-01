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
                "movement outcome uncertain");
  const auto replay = ledger.Reserve("base-0", "uncertain-1", false, "base_move:0.2");
  assert(replay.admission == StrictLedger::Admission::Prior);
  assert(!replay.result.accepted && replay.result.complete);
  assert(replay.result.error_message == "movement outcome uncertain");
  assert(ledger.Reserve("base-0", "uncertain-1", false, "base_move:0.3").admission ==
         StrictLedger::Admission::Conflict);
  assert(ledger.Reserve("base-0", "uncertain-1", true, "stop").admission ==
         StrictLedger::Admission::Conflict);
  assert(ledger.Reserve("arm-0", "uncertain-1", false, "arm_move:0.2").admission ==
         StrictLedger::Admission::New);
  std::cout << "uncertain released identity remains retained for this generation\n";
}
