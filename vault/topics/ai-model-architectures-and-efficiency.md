---
type: topic
status: active
first_seen: '2026-05-21'
last_covered: '2026-06-14'
mentions: 2
related_entities: []
---

# AI model architectures and efficiency

## Running summary

_2026-05-21:_ Sebastian Raschka analyzed how open-weight models tackle long-context efficiency by attacking the KV-cache problem through KV sharing, layer-wise attention budgeting, and compressed convolutional attention. ProxyCoT demonstrated that training models on short proxy context with supervised fine-tuning transfers reasoning capabilities to full long context with lower computational overhead. FlowLM proposed converting diffusion language models to flow matching through fine-tuning to match quality of multi-step diffusion sampling in fewer steps.

_2026-06-14:_ DiffusionGemma's diffusion-based generation achieves 1000+ tokens per second on H100 and 700+ on consumer RTX 5090, optimizing for latency-critical workflows; Gemma 4 12B eliminates separate vision and audio encoders, routing both directly into LLM backbone.

## Episode log
- 2026-05-21 — 2026-05-21 erdos-falls-google-io-and-the-ai-restructuring-wave
- 2026-06-14 — 2026-06-14 fable-five-and-the-starting-gun-of-ai-governance
