# examples/with_pdf_filler.py
"""
Example implementing a custom PDFFillerInterface.
"""
import os
import requests
from chatbot import chatbotClient, LocalStorage, FormConfig
from chatbot.pdf.interface import PDFFillerInterface


class MyPDFService(PDFFillerInterface):
    """Example: connect to a hypothetical REST PDF filling API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base = "https://api.my-pdf-service.com"

    def prepare_document(self, pdf_path: str, investor_type: str) -> str:
        r = requests.post(
            f"{self.base}/prepare",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"pdf_path": pdf_path, "investor_type": investor_type},
        )
        r.raise_for_status()
        return r.json()["doc_id"]

    def check_document_ready(self, doc_id: str) -> bool:
        r = requests.get(
            f"{self.base}/status/{doc_id}",
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        r.raise_for_status()
        return r.json()["status"] == "ready"

    def fill_document(self, doc_id: str, data_flat: dict):
        r = requests.post(
            f"{self.base}/fill/{doc_id}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"fields": data_flat},
        )
        r.raise_for_status()
        return r.json()["download_url"]


client = chatbotClient(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    storage=LocalStorage("./chatbot_data", "./configs"),
    form_config=FormConfig.from_directory("./configs"),
    pdf_filler=MyPDFService(api_key=os.getenv("PDF_SERVICE_KEY")),
)

# Register the PDF before starting the conversation
client.create_session(
    user_id="investor_789",
    session_id="session_pdf_001",
    pdf_path="/documents/lp_subscription_2024.pdf",
)

response, complete, data = client.send_message("investor_789", "session_pdf_001", "")
print(response)
