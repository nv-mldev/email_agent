# 📧 Email Agent - Auto-Read, Summarizer & Attachment Extractor

> **A comprehensive email processing system that automatically reads emails, generates summaries, and extracts attachments for further processing.**

## ✨ Features

- 📬 **Automated Email Reading** - Monitors and reads incoming emails
- 📝 **AI-Powered Summarization** - Generates concise email summaries
- 📎 **Attachment Extraction** - Securely extracts and processes email attachments
- 🔄 **Real-time Processing** - Uses RabbitMQ for efficient message queuing
- 🌐 **Microsoft Graph Integration** - Seamless integration with Office 365

## 📁 Project Structure

```
📂 email_agent/
├── 🔧 .env
├── 📋 requirements.txt
├── 🐍 .venv/
└── 📧 email_polling_service/
    ├── 🐍 __init__.py
    ├── ⚙️ config.py
    ├── 🌐 graph_client.py
    ├── ▶️ main.py
    ├── 🐰 rabbitmq_client.py
    └── 🔧 service.py
```

## 📋 File Descriptions

| File | Description |
|------|-------------|
| 🔧 **config.py** | Handles loading all configurations from environment variables |
| 🌐 **graph_client.py** | Contains refactored code to interact with MS Graph API |
| 🐰 **rabbitmq_client.py** | Utility to manage RabbitMQ connection and message publishing |
| 🔧 **service.py** | Core logic for the email polling service |
| ▶️ **main.py** | Entry point to start the service |

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Microsoft Azure account with Graph API access
- RabbitMQ server

### Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd email_agent
   ```

2. **Create virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the service**

   ```bash
   python email_polling_service/main.py
   ```

## ⚙️ Configuration

Set up the following environment variables in your `.env` file:

```env
# Microsoft Graph API
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=guest
RABBITMQ_PASSWORD=guest

# Email Configuration
MAILBOX_ADDRESS=your_email@domain.com
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p>Made with ❤️ for efficient email processing</p>
</div>
