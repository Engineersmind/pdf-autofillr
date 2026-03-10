# examples/with_s3_storage.py
"""
Example using S3Storage with your own AWS buckets.
Requires: pip install chatbot-sdk[s3]
"""
import os
from chatbot import chatbotClient, S3Storage, FormConfig

storage = S3Storage(
    output_bucket=os.environ["AWS_OUTPUT_BUCKET"],
    config_bucket=os.environ["AWS_CONFIG_BUCKET"],
    region=os.getenv("AWS_REGION", "us-east-1"),
)

client = chatbotClient(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    storage=storage,
    form_config=FormConfig.from_storage(storage),
    pdf_filler=None,
)

response, complete, data = client.send_message(
    user_id="investor_456",
    session_id="session_s3_001",
    message="",
)
print(response)
