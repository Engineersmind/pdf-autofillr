# Model Cards

One YAML config per model. These are passed to `run_benchmark.py` via `--model <name>`.

---

| Model | Provider | Cost | Context | Local |
|-------|----------|------|---------|-------|
| [gpt-4o](gpt-4o.yaml) | OpenAI | $$$ | 128k | No |
| [gpt-4o-mini](gpt-4o-mini.yaml) | OpenAI | $ | 128k | No |
| [claude-3-5-sonnet](claude-3-5-sonnet.yaml) | Anthropic | $$$ | 200k | No |
| [claude-3-5-haiku](claude-3-5-haiku.yaml) | Anthropic | $ | 200k | No |
| [llama3.1](llama3.1.yaml) | Meta via Ollama | Free | 128k | Yes |
| [mistral](mistral.yaml) | Mistral via Ollama | Free | 32k | Yes |

---

## Adding a new model

Create `models/<name>.yaml` following the same schema.
The `litellm_model` field is passed directly to `litellm.completion()`.
