// Experimental ExactScope Bridge -> ExecuTorch LLM runner adapter.
// This is not the frozen ExactScope C ABI.
#pragma once

#include "../bridge_contract.hpp"

#include <executorch/extension/llm/runner/irunner.h>

#include <cstdint>
#include <functional>
#include <string>

namespace exactscope::bridge::executorch {

struct Result {
  bool model_called;
  std::string payload;
};

using RenderMessages = std::function<std::string(const char* messages_json)>;

Result Run(const DeliveryView& delivery,
           ::executorch::extension::llm::IRunner& runner,
           const RenderMessages& render_messages,
           std::int32_t max_new_tokens = 32);

}  // namespace exactscope::bridge::executorch
