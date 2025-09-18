# Email Agent - React Frontend

A modern email agent with AI-powered summarization and React frontend for intelligent email processing and project ID extraction.

## 🚀 Quick Start

**Want to get started immediately?** → See the **[📋 STARTUP GUIDE](STARTUP_GUIDE.md)**

### One-Command Setup

**React UI:**

```bash
./quick_start_react.sh
```

Then visit: **<http://localhost:3000>**

## 🎯 Overview

This system automatically polls emails, extracts content, generates AI summaries, and provides a clean UI for email review. Perfect for email triage and quick communication overview.

## ✨ Key Features

- **📧 Email Ingestion**: Automatic polling from Microsoft Graph API
- **🤖 AI Summarization**: GPT-powered email content summarization  
- **🔢 Project ID Detection**: Automatic project identifier extraction
- **🎛️ Manual Controls**: "Fetch Emails" button for testing
- **📱 Clean UI**: Streamlit interface focused on summaries
- **⚡ Real-time Processing**: Background services with message queues

## 🏗️ Architecture

```
📧 Email Polling → 📝 Email Parser → 🤖 AI Summarizer → 📊 UI Display
     ↓              ↓              ↓             ↓
   Database     Extract Body    Generate       Show
              Store Metadata    Summary      Summaries
```

## 📁 Project Structure

```
├── api/                    # FastAPI REST endpoints
├── core/                   # Shared database, config, models
├── email_polling_service/  # Microsoft Graph email polling
├── email_parser_service/   # Email content extraction  
├── email_summarizer_service/ # AI summarization (NEW)
├── react-ui/              # Modern React frontend
├── .env                    # Configuration
├── requirements.txt        # Python dependencies
├── quick_start_react.sh    # One-command startup
└── README.md              # This file
```### 🔄 Workflow

1. **Email Ingestion**: Polls emails from Microsoft Graph API
2. **Basic Parsing**: Extracts email body and basic metadata
3. **AI Summarization**: Uses Azure OpenAI to generate concise summaries
4. **Project ID Extraction**: Automatically extracts project identifiers
5. **UI Display**: Shows emails with summaries in a clean interface

## 🚀 Getting Started

### Prerequisites
- PostgreSQL database
- RabbitMQ message broker
- Azure OpenAI service
- Microsoft Graph API credentials
- Node.js (for React UI - optional)

### Setup Environment
```bash
# Update .env with your credentials
cp .env.example .env
# Edit .env with your Azure and database credentials
```

### Install Dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt

# For React UI (optional)
cd react-ui && npm install && cd ..
```

### Start Services

```bash
./quick_start_react.sh
```

### Access Points

- **React UI**: <http://localhost:3000>
- **API Documentation**: <http://localhost:8000/docs>>

### 📊 Features

- **Manual Email Fetching**: Click "Fetch Emails" button to check for new messages
- **AI Summaries**: Automatic email summarization using GPT models
- **Project ID Detection**: Automatic extraction of project identifiers
- **Clean Interface**: Simple, focused UI for email review
- **Real-time Processing**: Background services process emails automatically

### 🔧 Configuration

Key environment variables in `.env`:

```bash
# Microsoft Graph API
AZURE_CLIENT_ID=your_client_id
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_SECRET=your_client_secret

# Email Configuration
MAILBOX_ADDRESS=your_email@domain.com

# Azure OpenAI (for summarization)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Database
DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/email_agent

# Storage (for future use)
AZURE_STORAGE_CONNECTION_STRING=your_storage_connection
```

### 📝 Notes

- This version focuses on email summarization rather than document analysis
- Document processing has been removed to simplify the architecture
- The system is perfect for email triage and quick overview of communications
- Future versions can add back document processing if needed

### 🛠️ Development

- **Logs**: Check `logs/` directory for service logs
- **Services**: Use `./check_services.sh` to monitor service status
- **Stopping**: Use `./stop_staging_services.sh` to stop all services
