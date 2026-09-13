// Experimental companion contract. This is NOT the frozen ExactScope C ABI.
#pragma once

#include <cstddef>

namespace exactscope::bridge {

enum class Action { complete, generate };
enum class Authority { authoritative, supplemental };
enum class State { grounded, none, ambiguous, conflict, unavailable };

struct TargetStateView {
  const char* target_key;
  Authority authority;
  State state;
};

struct DeliveryView {
  Action action;
  const char* route;
  const char* profile_sha256;
  const TargetStateView* states;
  std::size_t state_count;

  // action=complete: ExactScope-owned final reply JSON, no inference allowed.
  const char* reply_json;

  // action=generate: ExactScope-approved role/message array serialized as JSON.
  // The runtime adapter may apply its model-native chat template, but MUST NOT
  // reconstruct evidence from TargetStateView.
  const char* messages_json;
};

}  // namespace exactscope::bridge
