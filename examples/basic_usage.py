# examples/basic_usage.py
"""
Minimum working example — data-only mode with LocalStorage.
"""
import os
from chatbot import chatbotClient, LocalStorage, FormConfig

client = chatbotClient(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    storage=LocalStorage(data_path="./chatbot_data", config_path="./configs"),
    form_config=FormConfig.from_directory("./configs"),
    pdf_filler=None,  # data-only mode
)

# Simple REPL chat loop
user_id = "investor_123"
session_id = "session_001"

print("chatbot SDK — Basic Example")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() == "exit":
        break

    response, complete, data = client.send_message(
        user_id=user_id,
        session_id=session_id,
        message=user_input,
    )

    print(f"Bot: {response}\n")

    if complete:
        print("✅ Session complete!")
        print("Filled data:", data)
        break
