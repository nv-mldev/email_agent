# 🚀 Email Agent - Quick Start Guide

A modern email processin### What It Does:

1. ✅ Check prerequisites
2. ✅ Install Python dependencies
3. ✅ Install Node.js dependencies
4. ✅ Setup database tables
5. ✅ Start all services
6. ✅ Open browser to React UI with AI-powered summarization and project ID extraction.

## 📋 Table of Contents

- [🎯 Quick Setup](#-quick-setup)
- [📋 Prerequisites](#-prerequisites)
- [⚡ One-Command Setup](#-one-command-setup)
- [🔧 Manual Setup](#-manual-setup)
- [🌐 UI Options](#-ui-options)
- [📊 Monitoring](#-monitoring)
- [🛠️ Troubleshooting](#️-troubleshooting)
- [📚 Documentation](#-documentation)

## 🎯 Quick Setup

### One Command Setup

**React UI:**

```bash
# Complete setup and start with React interface
./quick_start_react.sh
```

**Access Point:**

- React UI: <http://localhost:3000>
- API Docs: <http://localhost:8000/docs>

---

## 📋 Prerequisites

### Required Services

- **PostgreSQL** (database)
- **RabbitMQ** (message queue)
- **Python 3.8+** (backend services)
- **Node.js 16+** (React UI)

### Azure Services

- **Microsoft Graph API** (email access)
- **Azure OpenAI** (AI summarization)
- **Azure Blob Storage** (optional - future attachments)

---

## ⚡ One-Command Setup

The quick start scripts handle everything automatically:

### What They Do

1. ✅ Check prerequisites
2. ✅ Install Python dependencies
3. ✅ Install Node.js dependencies (React mode)
4. ✅ Setup database tables
5. ✅ Start all services
6. ✅ Open browser to UI

### First Time Setup

```bash
# Clone or download the project
cd email_agent/ver3.0

# Make scripts executable
chmod +x *.sh

# Configure your environment
cp .env.example .env
# Edit .env with your credentials

# Start with React UI
./quick_start_react.sh
```

---

## 🔧 Manual Setup

If you prefer step-by-step setup:

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Create database tables
python create_tables.py

# Optional: Run migration if upgrading
python migrate_po_to_project_id.py
```

### 3. Configuration

```bash
# Copy and edit environment file
cp .env.example .env
# Update with your Azure credentials
```

### 4. Start Services

**React Mode:**

```bash
# Install React dependencies first
cd react-ui && npm install && cd ..

# Start React mode
./start_react_mode.sh
```

---

## 🌐 UI Options

### React UI (Modern - Recommended)

- **URL**: <http://localhost:3000>
- **Features**: Material-UI, data grid, responsive design
- **Best For**: Production, professional use

### Streamlit UI (Simple)

- **URL**: <http://localhost:8501>
- **Features**: Quick setup, Python-based
- **Best For**: Prototyping, data science workflows

### API Documentation

- **URL**: <http://localhost:8000/docs>
- **Features**: Interactive API docs, testing interface

---

## 📊 Monitoring

### Check Service Status

```bash
./check_services.sh
```

### View Logs

```bash
# Real-time log monitoring
tail -f logs/api.log         # API service
tail -f logs/parser.log      # Email parser
tail -f logs/summarizer.log  # AI summarizer
tail -f logs/react.log       # React UI (if using)
```

### Stop Services

```bash
# Stop Streamlit mode
./stop_staging_services.sh

# Stop React mode
./stop_react_services.sh
```

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check database exists
psql -U postgres -l

# Recreate tables
python create_tables.py
```

#### 2. RabbitMQ Connection Error

```bash
# Check RabbitMQ is running
sudo systemctl status rabbitmq-server

# Check management interface
curl http://localhost:15672
```

#### 3. Azure API Errors

- Verify credentials in `.env`
- Check Azure service quotas
- Ensure proper permissions

#### 4. React Build Issues

```bash
# Clear Node modules and reinstall
cd react-ui
rm -rf node_modules package-lock.json
npm install
npm start
```

#### 5. Port Already in Use

```bash
# Check what's using the port
lsof -i :3000  # React
lsof -i :8501  # Streamlit
lsof -i :8000  # API

# Kill processes if needed
kill $(lsof -t -i:3000)
```

### Debug Mode

```bash
# Start services with debug logging
DEBUG=1 ./start_react_mode.sh
```

---

## 📚 Documentation

### Core Documents

- [`README.md`](README.md) - Main project overview
- [`docs/UI_COMPARISON.md`](docs/UI_COMPARISON.md) - Streamlit vs React comparison
- [`docs/PROJECT_ID_MIGRATION.md`](docs/PROJECT_ID_MIGRATION.md) - Migration guide

### API Documentation

- **Live Docs**: <http://localhost:8000/docs> (when running)
- **Endpoints**: `/api/logs`, `/api/logs/{id}`, `/api/fetch-emails`

### React UI Documentation

- [`react-ui/README.md`](react-ui/README.md) - React-specific setup

---

## 🔄 Maintenance

### Database Cleanup

```bash
# Clean and reset database
./clean_before_run.sh
```

### Update Dependencies

```bash
# Python packages
pip install -r requirements.txt --upgrade

# Node.js packages (React mode)
cd react-ui && npm update && cd ..
```

### Backup Configuration

```bash
# Backup your environment settings
cp .env .env.backup
```

---

## 📞 Support

### Getting Help

1. **Check Logs**: Always check service logs first
2. **Verify Config**: Ensure `.env` is properly configured
3. **Test APIs**: Use the API docs to test endpoints
4. **Restart Services**: Try stopping and starting services

### Development Mode

```bash
# Start in development mode with auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## ✅ Success Checklist

After setup, verify everything works:

- [ ] All services start without errors
- [ ] UI loads and displays properly
- [ ] "Fetch Emails" button works
- [ ] Emails appear in the interface
- [ ] AI summaries are generated
- [ ] Project IDs are extracted
- [ ] No error messages in logs

**🎉 You're ready to use the Email Agent!**

---

*For advanced configuration and development details, see the full documentation in the [`docs/`](docs/) directory.*
