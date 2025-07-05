import math
import logging
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

from core.config import settings
from .config_keywords import DOCUMENT_TITLE_KEYWORDS_REGEX

logger = logging.getLogger(__name__)


class DocumentIntelligenceClientWrapper:
    """Synchronous client to analyze documents."""

    def __init__(self):
        self.endpoint = settings.AZURE_DOCUMENTINTELLIGENCE_ENDPOINT
        self.api_key = settings.AZURE_DOCUMENTINTELLIGENCE_API_KEY
        self.client = DocumentIntelligenceClient(
            endpoint=self.endpoint, credential=AzureKeyCredential(self.api_key)
        )

    def _get_font_weight_from_styles(self, result, span_offset, span_length):
        """Get font weight for a text span using document-level styles."""
        if not hasattr(result, "styles") or not result.styles:
            return None

        span_end = span_offset + span_length

        for style in result.styles:
            if hasattr(style, "spans") and style.spans:
                for style_span in style.spans:
                    style_start = style_span.offset
                    style_end = style_span.offset + style_span.length

                    # Check if spans overlap
                    if span_offset < style_end and span_end > style_start:
                        if hasattr(style, "font_weight"):
                            return style.font_weight
        return None

    def _is_bold_text(self, result, line):
        """Check if a line contains bold text using document styles."""
        if not line.spans:
            return False

        # Check each span in the line
        for span in line.spans:
            font_weight = self._get_font_weight_from_styles(
                result, span.offset, span.length
            )
            if font_weight == "bold":
                return True
        return False

    def _line_contains_any_bold_text(self, result, line):
        """Check if any part of a line overlaps with bold text spans."""
        if not line.spans or not hasattr(result, "styles") or not result.styles:
            return False

        line_start = line.spans[0].offset
        line_end = line.spans[-1].offset + line.spans[-1].length

        # Check if line overlaps with any bold style span
        for style in result.styles:
            if hasattr(style, "font_weight") and style.font_weight == "bold":
                if hasattr(style, "spans") and style.spans:
                    for style_span in style.spans:
                        style_start = style_span.offset
                        style_end = style_span.offset + style_span.length

                        # Check if spans overlap
                        if line_start < style_end and line_end > style_start:
                            return True
        return False

    def _get_font_family_from_styles(self, result, span_offset, span_length):
        """Get font family for a text span using document-level styles."""
        if not hasattr(result, "styles") or not result.styles:
            return None

        span_end = span_offset + span_length

        for style in result.styles:
            if hasattr(style, "spans") and style.spans:
                for style_span in style.spans:
                    style_start = style_span.offset
                    style_end = style_span.offset + style_span.length

                    # Check if spans overlap
                    if span_offset < style_end and span_end > style_start:
                        if hasattr(style, "similar_font_family"):
                            return style.similar_font_family
        return None

    def _filter_lines_by_font_properties(
        self, result, lines, prefer_bold=True, prefer_position=True
    ):
        """Filter lines based on font weight and position for title
        detection."""
        if not lines:
            return lines

        # First, try to get only bold lines
        bold_lines = []
        for line in lines:
            if self._line_contains_any_bold_text(result, line):
                bold_lines.append(line)

        # Check if any non-bold lines contain important document keywords
        keyword_lines = []
        important_keywords = [
            "certificate of analysis",
            "analysis certificate",
            "certificate of origin",
            "commercial invoice",
            "bill of lading",
            "air waybill",
            "sea waybill",
            "packing list",
            "inspection certificate",
        ]

        for line in lines:
            line_text = line.content.lower()
            for keyword in important_keywords:
                if keyword in line_text:
                    keyword_lines.append(line)
                    break

        # Combine bold lines and keyword lines, removing duplicates
        seen_lines = set()
        filtered_lines = []

        for line in lines:
            line_id = id(line)  # Use object ID for uniqueness
            is_in_bold = line in bold_lines
            is_in_keyword = line in keyword_lines
            if (is_in_bold or is_in_keyword) and line_id not in seen_lines:
                filtered_lines.append(line)
                seen_lines.add(line_id)

        if filtered_lines:
            return filtered_lines

        # Fallback: if no bold or keyword lines found, use position-based
        # filtering
        return lines

    def split_and_identify_by_title(self, blob_url: str) -> list:
        """
        Analyzes a document using position and keyword-based heuristics.
        Uses bold text detection combined with keyword matching for robust
        document type identification.
        """
        # Enable font extraction feature
        poller = self.client.begin_analyze_document(
            "prebuilt-layout",
            AnalyzeDocumentRequest(url_source=blob_url),
            features=["styleFont"],  # Enable font property extraction
        )
        result = poller.result()

        identified_docs = []
        if not result.pages:
            return []

        current_doc = None
        for page_num, page in enumerate(result.pages, 1):
            if not page.lines:
                continue

            # Calculate the number of lines in the top portion of the page
            num_lines_to_check = math.ceil(len(page.lines) * 0.25)  # Top 25%
            top_lines = page.lines[:num_lines_to_check]

            # Filter to get bold text lines and important keyword lines
            filtered_lines = self._filter_lines_by_font_properties(
                result, top_lines, prefer_bold=True, prefer_position=False
            )

            # Get the text content from filtered lines
            page_content = " ".join([line.content for line in filtered_lines])

            if not page_content:
                continue

            found_title = None
            found_match_length = 0  # Track the length of the matched text

            for doc_type, patterns in DOCUMENT_TITLE_KEYWORDS_REGEX.items():
                # Use regex to search for keywords in the top-section text
                for pattern in patterns:
                    match = pattern.search(page_content)
                    if match:
                        match_length = len(match.group())
                        # Prefer longer matches (more specific) over
                        # shorter ones
                        if match_length > found_match_length:
                            found_title = doc_type
                            found_match_length = match_length

            if found_title:
                if current_doc:
                    # Finalize the previous document before starting a new one
                    if current_doc["start_page"] <= page_num - 1:
                        current_doc["end_page"] = page_num - 1
                        identified_docs.append(current_doc)

                # Start the new document
                current_doc = {
                    "doc_type": found_title,
                    "confidence": 0.90,
                    "start_page": page_num,
                    "end_page": page_num,
                }

        # After the loop, add the last identified document if it exists
        if current_doc:
            current_doc["end_page"] = len(result.pages)
            identified_docs.append(current_doc)

        # If no documents were identified, classify as "unknown"
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

        system_prompt = (
            "You are an expert assistant for a logistics company. "
            "Summarize the following email content, focusing on the main "
            "intent, key entities, or instructions. Be concise."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text_to_summarize},
                ],
                temperature=0.2,
                max_tokens=150,
            )
            summary = response.choices[0].message.content
            return summary.strip() if summary else ""
        except Exception as e:
            logger.error("Error calling Azure OpenAI: %s", e)
            return f"Error generating summary: {e}"

    def extract_purchase_order_number(self, text: str) -> str:
        """Extract Purchase Order (PO) number from email content."""
        if not text:
            return ""

        system_prompt = (
            "You are an expert at extracting Purchase Order (PO) numbers from business emails. "
            "Look for patterns like 'PO:', 'P.O.:', 'Purchase Order:', 'PO Number:', 'PO#', "
            "'Order Number:', etc. followed by alphanumeric identifiers. "
            "Return ONLY the PO number if found, or 'Not Found' if no PO number is present. "
            "Examples: PO123456, P.O. ABC-789, Order #DEF456, etc."
        )

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract PO number from: {text}"},
                ],
                temperature=0.1,
                max_tokens=50,
            )
            po_number = response.choices[0].message.content
            extracted = po_number.strip() if po_number else "Not Found"

            # Return empty string if no PO found
            return extracted if extracted != "Not Found" else ""
        except Exception as e:
            logger.error("Error extracting PO number: %s", e)
            return ""
