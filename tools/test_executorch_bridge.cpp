// Compile/run smoke for the experimental ExactScope Bridge -> ExecuTorch adapter.
#include "../adapters/bridge/executorch/bridge_executorch.hpp"

#include <cassert>
#include <stdexcept>
#include <string>

namespace etllm = ::executorch::extension::llm;

class FakeRunner final : public etllm::IRunner {
 public:
  bool loaded = false;
  int generate_calls = 0;
  std::string last_prompt;
  etllm::GenerationConfig last_config;

  bool is_loaded() const override { return loaded; }
  ::executorch::runtime::Error load() override {
    loaded = true;
    return ::executorch::runtime::Error::Ok;
  }
  ::executorch::runtime::Error generate(
      const std::string& prompt,
      const etllm::GenerationConfig& config,
      std::function<void(const std::string&)> token_callback,
      std::function<void(const etllm::Stats&)> stats_callback) override {
    ++generate_calls;
    last_prompt = prompt;
    last_config = config;
    token_callback("{\"a\":");
    token_callback("\"Room 12\"}");
    stats_callback(etllm::Stats{});
    return ::executorch::runtime::Error::Ok;
  }
  void stop() override {}
  void reset() override {}
};

int main() {
  using namespace exactscope::bridge;
  using exactscope::bridge::executorch::Run;

  FakeRunner runner;
  bool rendered = false;
  const auto renderer = [&rendered](const char* messages_json) {
    rendered = true;
    assert(messages_json != nullptr);
    const std::string messages(messages_json);
    assert(messages.find("Room 12") != std::string::npos);
    return std::string("rendered prompt containing Room 12");
  };

  const DeliveryView complete{
      Action::complete,
      "host-grounded-scalar",
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      nullptr,
      0,
      "{\"a\":\"17 cm\",\"disposition\":\"answer\"}",
      nullptr,
  };
  const auto host_result = Run(complete, runner, renderer, 8);
  assert(!host_result.model_called);
  assert(host_result.payload.find("17 cm") != std::string::npos);
  assert(runner.generate_calls == 0);
  assert(!rendered);

  const DeliveryView generation{
      Action::generate,
      "grounded-context",
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      nullptr,
      0,
      nullptr,
      "[{\"role\":\"system\",\"content\":\"approved evidence\"},{\"role\":\"user\",\"content\":\"Room 12\"}]",
  };

  bool rejected_unloaded = false;
  try {
    (void)Run(generation, runner, renderer, 8);
  } catch (const std::invalid_argument&) {
    rejected_unloaded = true;
  }
  assert(rejected_unloaded);
  assert(runner.generate_calls == 0);

  assert(runner.load() == ::executorch::runtime::Error::Ok);
  const auto model_result = Run(generation, runner, renderer, 8);
  assert(model_result.model_called);
  assert(model_result.payload == "{\"a\":\"Room 12\"}");
  assert(runner.generate_calls == 1);
  assert(rendered);
  assert(runner.last_prompt.find("Room 12") != std::string::npos);
  assert(!runner.last_config.echo);
  assert(runner.last_config.max_new_tokens == 8);
  assert(runner.last_config.temperature == 0.0f);
  return 0;
}
