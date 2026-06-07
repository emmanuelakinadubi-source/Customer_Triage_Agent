# Customer Support Triage Agent

AI-powered automated triage system for customer support messages with both REST API and web UI.

## ✨ Features

- **Automated Message Analysis** - Categorizes, prioritizes, and analyzes customer messages
- **Single & Batch Processing** - Process one message or hundreds via API/UI
- **REST API** - Scalable backend for integration with existing systems
- **Web UI** - Streamlit interface for manual triage and file upload
- **Theme Support** - Light/Dark mode for user preference
- **Progress Indicators** - Real-time processing status display
- **Export Results** - Download CSV files with triage results
- **Containerized** - Docker support for easy deployment

## 🏗️ Architecture

```
FastAPI Backend (Port 8000)
├── /health             - Health check
├── /triage             - Single message triage
└── /triage/batch       - Batch processing

Streamlit UI (Port 8501)
├── Single Message Mode
├── Batch Upload Mode
└── Theme Settings
```

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone repository
git clone <repo-url>
cd customerReviews

# Build and start services
docker-compose build
docker-compose up

# Access services
# API:  http://localhost:8000
# UI:   http://localhost:8501
# Docs: http://localhost:8000/docs
```

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate

# Install API dependencies
pip install -r api/requirements.txt

# Install UI dependencies
pip install -r ui/requirements.txt

# Start API
cd api && uvicorn app.main:app --reload --port 8000

# Start UI (in new terminal)
cd ui && streamlit run app.py
```

## 📖 API Documentation

For detailed API reference, request/response examples, and integration guides, see [API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md).

### Quick API Examples

**Single Message:**
```bash
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"message": "I need help with my billing"}'
```

**Batch Messages:**
```bash
curl -X POST http://localhost:8000/triage/batch \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      "Billing issue",
      "Can't login",
      "Great product!"
    ]
  }'
```

## 📊 Response Format

```json
{
  "category": "Billing Issue",
  "urgency": "Medium",
  "urgency_reason": "Billing problems require resolution",
  "sentiment": "Frustrated",
  "suggested_owner": "Billing Department",
  "draft_response": "We will investigate immediately",
  "confidence": "High",
  "abusive_flag": false,
  "validation_status": "pending_implementation"
}
```

## 🎨 UI Features

### Input Modes
- **Single Message**: Enter text directly
- **Batch Upload**: Upload CSV/Excel with 'message' column

### Results Display
- Data grid with all triage fields
- Color-coded urgency levels
- CSV export functionality
- Error tracking and display

### Theme Support
- ☀️ Light mode
- 🌙 Dark mode

## 📁 Project Structure

```
customerReviews/
├── api/                          # FastAPI backend
│   ├── app/
│   │   ├── main.py              # App factory
│   │   ├── api/routes/          # Endpoints
│   │   ├── schemas/             # Pydantic models
│   │   ├── services/            # Business logic
│   │   ├── core/                # Config
│   │   └── utils/               # Helpers
│   ├── requirements.txt
│   └── Dockerfile
│
├── ui/                           # Streamlit frontend
│   ├── app.py                   # Main app
│   ├── components/              # UI components
│   ├── pages/                   # Pages
│   ├── utils/                   # Utilities
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml
├── README.md
└── API_INTEGRATION_GUIDE.md     # Detailed API docs
```

## 🔧 Configuration

### Environment Variables

Create `.env` file:
```env
API_URL=http://backend:8000
API_PORT=8000
DATABASE_URL=sqlite:///./app/data/triage.db
OPENAI_API_KEY=your_key_here
LLM_MODEL=gpt-4
```

## 📚 Documentation

- [API Integration Guide](API_INTEGRATION_GUIDE.md) - Complete API reference with examples
- [Architecture Overview](#-architecture) - System design
- [Docker Deployment](#using-docker-recommended) - Container setup

## 🛠️ Development

### Backend Development
```bash
cd api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd ui
pip install -r requirements.txt
streamlit run app.py
```

### Testing
```bash
# Run tests
cd api && pytest tests/

# Run UI tests
cd ui && pytest tests/
```

## 🐛 Troubleshooting

### API Connection Failed
- Check if API is running: `docker-compose logs api`
- Verify API_URL environment variable
- Check port 8000 is not in use

### No Results Display
- Verify CSV has 'message' column
- Check message values are non-empty
- Review API logs for errors

### Slow Processing
- Reduce batch size
- Check LLM API latency
- Monitor server resources

## 📞 Support

For issues or questions:
1. Check [API Integration Guide](API_INTEGRATION_GUIDE.md)
2. Review Docker logs: `docker-compose logs`
3. Check error messages in API responses

## 📝 License

TBD

## 👥 Team

For team integration and backend development, see [API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md) for:
- JSON request/response formats
- Integration examples (Python, JavaScript)
- Database integration patterns
- Webhook setup
