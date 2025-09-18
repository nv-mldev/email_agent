import logging
import json
from openai import AzureOpenAI
from core.config import settings

logger = logging.getLogger(__name__)


class AzureOpenAIClient:
    """Client for Azure OpenAI API to generate email summaries and analyze attachments."""

    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-02-01",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        )
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME

    def summarize_email(
        self, email_body: str, subject: str = "", sender: str = ""
    ) -> str:
        """Generate a concise summary of the email content."""
        try:
            # Create a comprehensive prompt for email summarization
            prompt = f"""
Please provide a concise, professional summary of the following email in
2-3 sentences. Focus on the main purpose, key points, and any action items
or important information.

Email Subject: {subject}
From: {sender}

Email Content:
{email_body}

Summary:"""

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that creates "
                            "concise, professional email summaries. "
                            "Focus on extracting main purpose, key "
                            "information, and action items from "
                            "emails."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.3,
            )

            summary = response.choices[0].message.content
            if summary:
                summary = summary.strip()
            else:
                summary = "No summary could be generated."

            logger.info("Successfully generated email summary")
            return summary

        except Exception as e:
            logger.error("Failed to generate email summary: %s", e)
            return f"Error generating summary: {str(e)}"

    def extract_project_id(self, email_body: str, subject: str = "") -> str | None:
        """Extract project ID from email content."""
        try:
            prompt = f"""
Extract the project ID from the following email if present.
Look for patterns like: Project ID, Project #, Project Number, Proj ID,
Project Code, etc. Return only the identifier, or "None" if no project ID
is found.

Email Subject: {subject}
Email Content:
{email_body}

Project ID:"""

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an assistant that extracts "
                            "project IDs from emails. "
                            "Return only the Project ID if found, or "
                            "'None' if not found."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=50,
                temperature=0.1,
            )

            project_id = response.choices[0].message.content
            if project_id:
                project_id = project_id.strip()
                if project_id.lower() in ["none", "n/a", "not found", ""]:
                    return None

                logger.info("Extracted Project ID: %s", project_id)
                return project_id

            return None

        except Exception as e:
            logger.error("Failed to extract Project ID: %s", e)
            return None

    def analyze_attachments(
        self, attachment_filenames: list[str], email_context: str = ""
    ) -> dict:
        """Analyze attachment content and provide insights."""
        try:
            # Create a comprehensive prompt for attachment analysis
            filenames_text = ", ".join(attachment_filenames)
            prompt = f"""
Analyze the following attachment files based on their filenames and email context.
Provide insights about document type, purpose, and likely content.

Email Context: {email_context}
Attachment Filenames: {filenames_text}

Please provide:
1. Document Type (e.g., Technical Specification, Proposal, Contract, etc.)
2. Summary of likely content and purpose
3. Key points that might be covered
4. Technical details or important aspects

Respond in JSON format:
{{
    "document_type": "type here",
    "summary": "comprehensive summary here", 
    "key_points": ["point1", "point2", "point3"],
    "technical_details": {{"aspect1": "detail1", "aspect2": "detail2"}}
}}"""

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a document analysis expert that can "
                            "determine document types and content from "
                            "filenames and context. Provide structured "
                            "analysis in JSON format."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
                temperature=0.3,
            )

            analysis_text = response.choices[0].message.content
            if analysis_text:
                try:
                    # Try to parse as JSON
                    analysis_data = json.loads(analysis_text.strip())
                    logger.info("Successfully analyzed attachments")
                    return analysis_data
                except json.JSONDecodeError:
                    # Fallback to text response
                    logger.warning("Could not parse JSON, using text response")
                    return {
                        "document_type": "Unknown",
                        "summary": analysis_text.strip(),
                        "key_points": ["Analysis provided in summary"],
                        "technical_details": {}
                    }
            else:
                return {
                    "document_type": "Unknown",
                    "summary": "No analysis could be generated.",
                    "key_points": [],
                    "technical_details": {}
                }

        except Exception as e:
            logger.error("Failed to analyze attachments: %s", e)
            return {
                "document_type": "Error",
                "summary": f"Error analyzing attachments: {str(e)}",
                "key_points": [],
                "technical_details": {}
            }

    def analyze_attachments_with_content(
        self, attachments_data: list[dict], email_context: str = ""
    ) -> dict:
        """Analyze attachment content with actual file data and metadata."""
        try:
            # Prepare analysis context
            context_parts = [f"Email Context: {email_context}"]
            
            for i, attachment in enumerate(attachments_data, 1):
                filename = attachment.get("filename", "unknown")
                content_preview = attachment.get("content_preview", "")
                file_type = attachment.get("content_type", "unknown")
                size = attachment.get("size", 0)
                
                context_parts.append(f"""
Attachment {i}:
- Filename: {filename}
- Type: {file_type}
- Size: {size} bytes
- Content preview: {content_preview[:500]}...
""")
            
            full_context = "\n".join(context_parts)
            
            prompt = f"""
Analyze the following email attachments based on their content and metadata.
Provide comprehensive insights about document types, purpose, and key information.

{full_context}

Please provide detailed analysis in JSON format:
{{
    "document_type": "primary document type",
    "summary": "comprehensive analysis of all attachments",
    "key_points": ["specific insight 1", "insight 2", "insight 3"],
    "technical_details": {{
        "file_types": ["list of file types"],
        "estimated_content": "what the documents likely contain",
        "business_relevance": "how this relates to business operations",
        "priority_level": "high/medium/low based on content"
    }}
}}"""

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert document analyst with deep "
                            "knowledge of business documents, technical "
                            "specifications, contracts, and project materials. "
                            "Provide detailed, actionable insights in JSON format."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,
                temperature=0.2,
            )

            analysis_text = response.choices[0].message.content
            if analysis_text:
                try:
                    analysis_data = json.loads(analysis_text.strip())
                    logger.info("Successfully analyzed attachments with content")
                    return analysis_data
                except json.JSONDecodeError:
                    logger.warning("Could not parse JSON, using text response")
                    return {
                        "document_type": "Mixed Documents",
                        "summary": analysis_text.strip(),
                        "key_points": ["Analysis provided in summary"],
                        "technical_details": {
                            "file_types": [att.get("content_type", "unknown") for att in attachments_data],
                            "estimated_content": "Content analysis available in summary",
                            "business_relevance": "Requires manual review",
                            "priority_level": "medium"
                        }
                    }
            else:
                return self._default_analysis_result(attachments_data)

        except Exception as e:
            logger.error("Failed to analyze attachments with content: %s", e)
            return {
                "document_type": "Error",
                "summary": f"Error analyzing attachments: {str(e)}",
                "key_points": ["Analysis failed due to error"],
                "technical_details": {
                    "file_types": [att.get("content_type", "unknown") for att in attachments_data],
                    "estimated_content": "Unable to analyze due to error",
                    "business_relevance": "Unknown",
                    "priority_level": "unknown"
                }
            }
    
    def _default_analysis_result(self, attachments_data: list[dict]) -> dict:
        """Return default analysis result when content analysis fails."""
        return {
            "document_type": "Unknown",
            "summary": "Content analysis could not be completed",
            "key_points": ["Manual review required"],
            "technical_details": {
                "file_types": [att.get("content_type", "unknown") for att in attachments_data],
                "estimated_content": "Content analysis unavailable",
                "business_relevance": "Requires manual review",
                "priority_level": "medium"
            }
        }
- Filename: {filename}
- Type: {file_type}
- Size: {size} bytes
- Content preview: {content_preview[:500]}...
""")
            
            full_context = "\n".join(context_parts)
            
            prompt = f"""
Analyze the following email attachments based on their content and metadata.
Provide comprehensive insights about document types, purpose, and key information.

{full_context}

Please provide detailed analysis in JSON format:
{{
    "document_type": "primary document type",
    "summary": "comprehensive analysis of all attachments",
    "key_points": ["specific insight 1", "insight 2", "insight 3"],
    "technical_details": {{
        "file_types": ["list of file types"],
        "estimated_content": "what the documents likely contain",
        "business_relevance": "how this relates to business operations",
        "priority_level": "high/medium/low based on content"
    }}
}}"""

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert document analyst with deep "
                            "knowledge of business documents, technical "
                            "specifications, contracts, and project materials. "
                            "Provide detailed, actionable insights in JSON format."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,
                temperature=0.2,
            )

            analysis_text = response.choices[0].message.content
            if analysis_text:
                try:
                    analysis_data = json.loads(analysis_text.strip())
                    logger.info("Successfully analyzed attachments with content")
                    return analysis_data
                except json.JSONDecodeError:
                    logger.warning("Could not parse JSON, using text response")
                    return {
                        "document_type": "Mixed Documents",
                        "summary": analysis_text.strip(),
                        "key_points": ["Analysis provided in summary"],
                        "technical_details": {
                            "file_types": [att.get("content_type", "unknown") for att in attachments_data],
                            "estimated_content": "Content analysis available in summary",
                            "business_relevance": "Requires manual review",
                            "priority_level": "medium"
                        }
                    }
            else:
                return self._default_analysis_result(attachments_data)

        except Exception as e:
            logger.error("Failed to analyze attachments with content: %s", e)
            return {
                "document_type": "Error",
                "summary": f"Error analyzing attachments: {str(e)}",
                "key_points": ["Analysis failed due to error"],
                "technical_details": {
                    "file_types": [att.get("content_type", "unknown") for att in attachments_data],
                    "estimated_content": "Unable to analyze due to error",
                    "business_relevance": "Unknown",
                    "priority_level": "unknown"
                }
            }
    
    def _default_analysis_result(self, attachments_data: list[dict]) -> dict:
        """Return default analysis result when content analysis fails."""
        return {
            "document_type": "Unknown",
            "summary": "Content analysis could not be completed",
            "key_points": ["Manual review required"],
            "technical_details": {
                "file_types": [att.get("content_type", "unknown") for att in attachments_data],
                "estimated_content": "Content analysis unavailable",
                "business_relevance": "Requires manual review",
                "priority_level": "medium"
            }
        }
