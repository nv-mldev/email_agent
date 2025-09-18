# React UI for Email Agent

A modern React frontend for the Email Agent system, built with Material-UI components.

## 🎯 Features

- **📊 Data Grid**: Interactive table for email management
- **🎨 Material-UI**: Modern, responsive design
- **⚡ Real-time Updates**: Fetch emails and refresh data
- **📱 Mobile Friendly**: Responsive layout
- **🔍 Email Details**: Click any row to view full email details\n- **🤖 AI Summaries**: Display AI-generated email summaries\n- **PO Number**: Highlighted purchase order detection

## 🚀 Quick Start

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- Running FastAPI backend

### Installation

1. **Install React dependencies:**

   ```bash
   cd react-ui
   npm install
   ```

2. **Start the React development server:**

   ```bash
   npm start
   ```

3. **Or use the automated script:**

   ```bash
   # From the main project directory
   ./start_react_mode.sh
   ```

## 🌐 Access Points

- **React UI**: <http://localhost:3000>
- **API Backend**: <http://localhost:8000>
- **API Documentation**: <http://localhost:8000/docs>

## 📁 Project Structure

```
react-ui/
├── public/
│   └── index.html          # HTML template
├── src/
│   ├── App.js             # Main React component
│   ├── index.js           # Entry point
│   └── index.css          # Global styles
├── package.json           # Dependencies
└── README.md             # This file
```

## 🎨 UI Components

### Main Dashboard

- **Header**: Title and last updated timestamp
- **Action Buttons**: Fetch emails and refresh
- **Email Grid**: Sortable, filterable data table
- **Status Chips**: Color-coded email processing status

### Email Details

- **Summary Card**: Email subject, sender, status
- **Project ID**: Highlighted project identifier detection
- **AI Summary**: Expandable section with generated summary
- **Email Body**: Full email content in formatted text
- **Attachments**: List of email attachments

## 🔧 Configuration

The React app uses a proxy configuration to communicate with the FastAPI backend:

```json
{
  "proxy": "http://localhost:8000"
}
```

## 📊 Status Colors

- **🔵 RECEIVED**: Blue (info)
- **🟡 PARSING**: Orange (warning)  
- **🟢 PARSED**: Green (success)
- **🟣 ANALYZING**: Purple (secondary)
- **✅ COMPLETE**: Dark green (success)
- **🔴 FAILED**: Red (error)

## 🛠️ Development

### Available Scripts

- `npm start`: Start development server
- `npm run build`: Build for production
- `npm test`: Run tests
- `npm run eject`: Eject from Create React App

### Custom Styling

Status-specific CSS classes are available:

- `.status-received`
- `.status-parsing`
- `.status-parsed`
- `.status-analyzing`
- `.status-complete`
- `.status-failed`

## 🔄 API Integration

The React app communicates with these FastAPI endpoints:

- `GET /api/logs` - Fetch all email logs
- `GET /api/logs/{id}` - Fetch specific email details
- `POST /api/fetch-emails` - Manually trigger email fetching

## 📱 Responsive Design

The UI is fully responsive and works on:

- **Desktop**: Full data grid with all columns
- **Tablet**: Responsive grid layout
- **Mobile**: Stacked cards and collapsible sections

## 🚀 Production Build

To create a production build:

```bash
npm run build
```

This creates an optimized build in the `build/` directory ready for deployment.

## 🔧 Troubleshooting

**Common Issues:**

1. **CORS errors**: Ensure the FastAPI backend has CORS middleware configured
2. **API connection**: Verify the backend is running on port 8000
3. **Build errors**: Check Node.js version compatibility

**Debug Steps:**

1. Check browser console for errors
2. Verify API endpoints in browser dev tools
3. Ensure all dependencies are installed
4. Check the proxy configuration in package.json
