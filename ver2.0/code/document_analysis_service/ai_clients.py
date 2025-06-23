# Use the standard, synchronous OpenAI client
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

from core.config import settings

# This keyword dictionary remains the same
DOCUMENT_TITLE_KEYWORDS = {
    "invoice": ["invoice", "bill to", "remittance"],
    "purchase_order": ["purchase order", "po number"],
    "eway_bill": ["e-way bill", "eway bill"],
    "bill_of_lading": ["bill of lading", "bol"],
    "packing_list": ["packing list", "packing slip"],
}


class DocumentIntelligenceClientWrapper:
    """Synchronous client to analyze documents."""

    def __init__(self):
        self.endpoint = settings.AZURE_DOCUMENTINTELLIGENCE_ENDPOINT
        self.api_key = settings.AZURE_DOCUMENTINTELLIGENCE_API_KEY
        self.client = DocumentIntelligenceClient(
            endpoint=self.endpoint, credential=AzureKeyCredential(self.api_key)
        )

    def split_and_identify_by_title(self, blob_url: str) -> list:
        """
        Analyzes a document using a blocking call.
        """
        # begin_analyze_document is a sync call that returns a poller
        poller = self.client.begin_analyze_document(
            "prebuilt-layout", AnalyzeDocumentRequest(url_source=blob_url)
        )

        # .result() is a sync, blocking call that waits for the operation to complete
        result = poller.result()

        identified_docs = []
        if not result.pages:
            return []

        current_doc = None
        for page_num, page in enumerate(result.pages, 1):
            page_content = " ".join([line.content for line in page.lines]).lower()
            found_title = None
            for doc_type, keywords in DOCUMENT_TITLE_KEYWORDS.items():
                if any(keyword in page_content for keyword in keywords):
                    found_title = doc_type
                    break

            if found_title:
                if current_doc:
                    current_doc["end_page"] = page_num - 1
                    identified_docs.append(current_doc)
                current_doc = {
                    "doc_type": found_title,
                    "confidence": 0.90,
                    "start_page": page_num,
                    "end_page": page_num,
                }
                print(f"  -> Found title for '{found_title}' on page {page_num}")

        if current_doc:
            current_doc["end_page"] = len(result.pages)
            identified_docs.append(current_doc)

        if not identified_docs and len(result.pages) > 0:
            identified_docs.append(
                {
                    "doc_type": "unknown",
                    "confidence": 0.50,
                    "start_page": 1,
                    "end_page": len(result.pages),
                }
            )

        return identified_docs


class OpenAIClientWrapper:
    """Synchronous client to summarize email text."""

    def __init__(self):
        # Use the standard synchronous client
        self.client = AzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-02-01",
        )
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME

    def summarize_email_body(self, text_to_summarize: str) -> str:
        """Generates a concise summary of the email body."""
        if not text_to_summarize:
            return ""

        system_prompt = "You are an expert assistant for a logistics company. Summarize the following email content, focusing on the main intent, key entities, or instructions. Be concise."

        try:
            # This is now a standard, synchronous function call
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text_to_summarize},
                ],
                temperature=0.2,
                max_tokens=150,
            )
            summary = response.choices[0].message.content.strip()
            print(f"  -> Generated email summary: '{summary}'")
            return summary
        except Exception as e:
            print(f"Error calling Azure OpenAI: {e}")
            return f"Error generating summary: {e}"
