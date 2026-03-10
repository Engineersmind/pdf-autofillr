# chatbot/managed/__init__.py
"""
chatbot Managed PDF Service — NOT included in the open source SDK.

Install separately: pip install chatbot-managed
Requires a paid API key from chatbot.io

    from chatbot.managed import chatbotManagedPDFFiller

    client = chatbotClient(
        ...,
        pdf_filler=chatbotManagedPDFFiller(api_key='chatbot_sk_...')
    )
"""

def __getattr__(name):
    if name in ("chatbotManagedPDFFiller", "chatbotManagedConfig"):
        raise ImportError(
            f"{name} is not available in the open source SDK.\n"
            "Install the managed package: pip install chatbot-managed\n"
            "Obtain an API key at: https://chatbot.io"
        )
    raise AttributeError(f"module 'chatbot.managed' has no attribute {name!r}")
