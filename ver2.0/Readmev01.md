# System Architecture and Design (Revised)

This document details the architecture for an AI agent that processes emails from a designated inbox, identifies document types, and then presents them to a user for confirmation before final data extraction.

## Component Breakdown (Revised)

This revised flow places the automated document identification before the user interaction step.

### 📨 Email Polling Service

- Continuously monitors the `hello@cargoa.io` inbox for new emails.
- Can use webhooks (real-time) or scheduled polling.

### 🗂️ Email Parser

- Extracts key information from new emails:
  - Sender
  - Subject
  - Body
  - Attachments

### 📝 Email Summarizer

- Passes the email body to a large language model (LLM).
- Generates a concise summary for user context on the UI dashboard.

### 📎 Attachment Handler

- Securely transfers attachments to cloud storage (e.g., AWS S3, Google Cloud Storage).
- Ensures original files are saved before processing.

### 🏷️ Document Identifier

- Analyzes stored attachments using a machine learning model.
- Automatically identifies document type (e.g., Invoice, Purchase Order, E-way Bill).

### 🖥️ UI Dashboard

- Main interface for human-in-the-loop.
- Displays:
  - Email summary
  - List of attachments
  - Predicted document type for each attachment

### 👤 Human Confirmation

- User reviews dashboard information.
- Confirms or overrides predicted document type.
- Confirmation triggers the next processing stage.

### 🔗 Extraction APIs

- Upon confirmation, dispatches documents to specific extraction APIs:
  - 🧾 Invoice Extraction API
  - 📄 Purchase Order Extraction API
  - 🚚 E-way Bill Extraction API

### 🗃️ Processed Data

- Final structured data is stored in a database or sent to downstream systems.

---

## 🚀 Development and Deployment Strategy

The technology stack and deployment strategy remain robust and suitable for this revised workflow.

### 🛠️ Technology Stack

- **Backend:** Python (TensorFlow, PyTorch, Scikit-learn, Flask, Django)
- **Frontend:** React or Vue.js for the interactive UI dashboard
- **AI/ML Models:**
  - Email Summarization: Pre-trained LLMs (OpenAI GPT, Google Gemini, Hugging Face)
  - Document Identification: Custom models (TensorFlow, PyTorch) or cloud AI services (Google Cloud Vision AI, AWS Rekognition)
- **Storage:** Cloud object storage (AWS S3, Google Cloud Storage, Azure Blob Storage)

### ⚙️ Deployment

- **Containerization:** Docker for packaging microservices
- **Orchestration:** Kubernetes (Amazon EKS, Google GKE, Azure AKS)
- **CI/CD:** GitHub Actions, Jenkins, or GitLab CI
- **Monitoring:** Prometheus (metrics), Grafana (visualization), ELK Stack (logging)

## POSTGRESQL

### Creating Tables

```bash
sudo -u postgres psql 
CREATE ROLE cargoa_user WITH LOGIN PASSWORD 'mysecretpassword';
CREATE DATABASE email_agent WITH OWNER = cargoa_user;
```

### Deleting the Tables in Postgresql

```bash
sudo -u postgres psql -c "DROP DATABASE email_agent;"
```

or

```bash
sudo -u postgres psql
DROP DATABASE email_agent;
\q
```

`
