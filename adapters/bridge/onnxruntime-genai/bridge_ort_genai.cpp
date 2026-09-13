// Experimental ExactScope Bridge -> ONNX Runtime GenAI prototype.
// ORT owns model loading, tokenization and generation. ExactScope owns delivery.
#include "../bridge_contract.hpp"
#include "ort_genai.h"

#include <cstddef>
#include <stdexcept>
#include <string>

namespace exactscope::bridge::ort_genai {

std::string Run(const DeliveryView& delivery,
                OgaModel* model,
                OgaTokenizer* tokenizer,
                const char* chat_template,
                std::size_t max_new_tokens) {
  if (delivery.action == Action::complete) {
    if (delivery.reply_json == nullptr || delivery.messages_json != nullptr) {
      throw std::invalid_argument("invalid deterministic ExactScope delivery");
    }
    return delivery.reply_json;  // No ORT call on this path.
  }

  if (delivery.action != Action::generate || delivery.reply_json != nullptr ||
      delivery.messages_json == nullptr || model == nullptr || tokenizer == nullptr ||
      chat_template == nullptr || max_new_tokens == 0) {
    throw std::invalid_argument("invalid generation ExactScope delivery");
  }

  // Model-specific formatting remains runtime/host-owned. Bridge passes the exact
  // ExactScope-approved role messages and never rebuilds evidence from grounding state.
  auto prompt = tokenizer->ApplyChatTemplate(
      chat_template, delivery.messages_json, "", true);
  auto input = OgaSequences::Create();
  tokenizer->Encode(prompt, *input);
  if (input->Count() != 1) {
    throw std::runtime_error("Bridge prototype requires one input sequence");
  }
  const std::size_t input_length = input->SequenceCount(0);

  auto params = OgaGeneratorParams::Create(*model);
  params->SetSearchOption("max_length",
                          static_cast<double>(input_length + max_new_tokens));
  params->SetSearchOption("batch_size", 1.0);
  params->SetSearchOptionBool("do_sample", false);

  auto generator = OgaGenerator::Create(*model, *params);
  generator->AppendTokenSequences(*input);
  while (!generator->IsDone()) {
    generator->GenerateNextToken();
  }

  const std::size_t total = generator->GetSequenceCount(0);
  if (total < input_length) {
    throw std::runtime_error("ORT GenAI returned a sequence shorter than its input");
  }
  auto decoded = tokenizer->Decode(generator->GetSequenceData(0) + input_length,
                                   total - input_length);
  return std::string(static_cast<const char*>(decoded));
}

}  // namespace exactscope::bridge::ort_genai
