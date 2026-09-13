// Experimental ExactScope Bridge -> ExecuTorch LLM runner adapter.
#include "bridge_executorch.hpp"

#include <stdexcept>
#include <string>

namespace exactscope::bridge::executorch {

Result Run(const DeliveryView& delivery,
           ::executorch::extension::llm::IRunner& runner,
           const RenderMessages& render_messages,
           std::int32_t max_new_tokens) {
  if (delivery.action == Action::complete) {
    if (delivery.reply_json == nullptr || delivery.messages_json != nullptr) {
      throw std::invalid_argument("invalid deterministic ExactScope delivery");
    }
    return Result{false, delivery.reply_json};
  }

  if (delivery.action != Action::generate || delivery.reply_json != nullptr ||
      delivery.messages_json == nullptr || !render_messages ||
      max_new_tokens <= 0) {
    throw std::invalid_argument("invalid generation ExactScope delivery");
  }
  if (!runner.is_loaded()) {
    throw std::invalid_argument(
        "ExecuTorch runner must be loaded by the host before Bridge generation");
  }

  const std::string prompt = render_messages(delivery.messages_json);
  if (prompt.empty()) {
    throw std::invalid_argument("host message renderer produced an empty prompt");
  }

  ::executorch::extension::llm::GenerationConfig config;
  config.echo = false;
  config.max_new_tokens = max_new_tokens;
  config.temperature = 0.0f;

  std::string raw_generation;
  const auto error = runner.generate(
      prompt,
      config,
      [&raw_generation](const std::string& token_text) {
        raw_generation += token_text;
      },
      [](const ::executorch::extension::llm::Stats&) {});

  if (error != ::executorch::runtime::Error::Ok) {
    throw std::runtime_error("ExecuTorch generation failed");
  }
  return Result{true, std::move(raw_generation)};
}

}  // namespace exactscope::bridge::executorch
