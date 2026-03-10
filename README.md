# chatbot SDK

> Conversational investor onboarding chatbot — open source Python SDK

[![PyPI version](https://badge.fury.io/py/chatbot-sdk.svg)](https://badge.fury.io/py/chatbot-sdk)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

chatbot SDK powers conversational investor onboarding. It runs a stateful chatbot that collects investor information through natural language, validates it, and produces a filled data dict (and optionally a filled PDF).

## Features

- 13-state conversation engine guides investors through form completion
- GPT-4o-mini extracts structured data from natural language input
- Phone validation, address auto-copy, skip/exit intent detection
- Per-user profile tracking across sessions for faster repeat onboarding
- Produces `final_output_flat.json` ready for any PDF service
- Pluggable PDF filling via `PDFFillerInterface`
- Local filesystem or S3 storage backends
- Optional telemetry with full PII anonymization

## Installation

```bash
# Core only
pip install chatbot-sdk

# With S3 storage support
pip install chatbot-sdk[s3]

# With local FastAPI server
pip install chatbot-sdk[server]

# Everything
pip install chatbot-sdk[all]
```

## Quick Start

```python
import os
from chatbot import chatbotClient, LocalStorage, FormConfig

client = chatbotClient(
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    storage=LocalStorage(data_path='./data', config_path='./configs'),
    form_config=FormConfig.from_directory('./configs'),
    pdf_filler=None   # data-only mode
)

response, complete, data = client.send_message(
    user_id='investor_123',
    session_id='session_abc',
    message=user_input
)

if complete:
    filled = client.get_session_data('investor_123', 'session_abc')
    print(filled)
```

## Documentation

Full technical reference: [docs.chatbot.io](https://docs.chatbot.io)

## License

MIT
