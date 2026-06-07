# Customer Support Triage Agent - API Integration Guide

## Overview

The Customer Support Triage Agent is an AI-powered system that automatically analyzes customer messages and triages them based on category, urgency, sentiment, and other metrics. The system provides both REST API endpoints and a web UI for single message and batch processing.

## Project Architecture

```
customer-reviews/
├── api/                          # FastAPI backend
│   ├── app/
│   │   ├── main.py              # FastAPI application factory
│   │   ├── api/routes/          # API endpoint handlers
│   │   │   ├── health.py        # Health check endpoint
│   │   │   └── triage.py        # Triage endpoints (single & batch)
│   │   ├── schemas/             # Pydantic models (request/response)
│   │   ├── services/            # Business logic
│   │   │   └── triage_service.py
│   │   ├── guards/              # Input/output validation guards
│   │   ├── prompts/             # LLM prompt templates
│   │   ├── db/                  # Database models and session
│   │   ├── core/                # Config and constants
│   │   └── utils/               # Helper utilities
│   ├── requirements.txt
│   └── Dockerfile
│
├── ui/                           # Streamlit frontend
│   ├── app.py                   # Main Streamlit app
│   ├── components/              # Reusable UI components
│   │   ├── message_input.py
│   │   ├── result_card.py
│   │   └── batch_table.py
│   ├── pages/                   # Streamlit pages
│   │   └── batch_triage.py      # Triage form & processing
│   ├── utils/                   # Utilities
│   │   └── api_client.py        # API client wrapper
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml           # Multi-container orchestration
├── README.md
└── API_INTEGRATION_GUIDE.md     # This file
```

## API Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API is running and healthy.

**Request:**
```bash
curl -X GET http://localhost:8000/health
```

**Response (200 OK):**
```json
{
  "status": "ok"
}
```

---

### 2. Single Message Triage

**Endpoint:** `POST /triage`

**Description:** Analyze a single customer message.

**Request:**
```bash
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have a billing issue with my account"
  }'
```

**Request Schema:**
```json
{
  "message": "string (required, min length 1)"
}
```

**Response (200 OK):**
```json
{
  "category": "Billing Issue",
  "urgency": "Medium",
  "urgency_reason": "The message indicates a billing problem that needs resolution.",
  "sentiment": "Frustrated",
  "suggested_owner": "Billing Department",
  "draft_response": "Thank you for reporting your billing issue. We will investigate this immediately.",
  "confidence": "High",
  "abusive_flag": false,
  "validation_status": "pending_implementation"
}
```

**Response Fields:**
- `category` (string): Message category (e.g., "Billing Issue", "Technical Support", "General Enquiry")
- `urgency` (string): Priority level - "Low", "Medium", "High", "Critical"
- `urgency_reason` (string): Explanation for the urgency level
- `sentiment` (string): Detected sentiment - "Positive", "Neutral", "Negative", "Frustrated"
- `suggested_owner` (string): Recommended department to handle the message
- `draft_response` (string): AI-generated response draft
- `confidence` (string): Confidence level - "Low", "Medium", "High"
- `abusive_flag` (boolean): Whether the message contains abusive content
- `validation_status` (string): Processing status

---

### 3. Batch Message Triage

**Endpoint:** `POST /triage/batch`

**Description:** Analyze multiple customer messages in a single request (for CSV/Excel uploads or bulk processing).

**Request:**
```bash
curl -X POST http://localhost:8000/triage/batch \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      "I have a billing issue",
      "Can you help me reset my password?",
      "I love your service!"
    ]
  }'
```

**Request Schema:**
```json
{
  "messages": [
    "string",
    "string",
    "..."
  ]
}
```

**Response (200 OK):**
```json
{
  "results": [
    {
      "message": "I have a billing issue",
      "category": "Billing Issue",
      "urgency": "Medium",
      "urgency_reason": "The message indicates a billing problem that needs resolution.",
      "sentiment": "Neutral",
      "suggested_owner": "Billing Department",
      "draft_response": "Thank you for reporting. Our billing team will assist you.",
      "confidence": "High",
      "abusive_flag": false,
      "validation_status": "pending_implementation"
    },
    {
      "message": "Can you help me reset my password?",
      "category": "Technical Support",
      "urgency": "Low",
      "urgency_reason": "Password reset is a routine support request.",
      "sentiment": "Neutral",
      "suggested_owner": "Technical Support",
      "draft_response": "We can help you reset your password. Please check your email.",
      "confidence": "High",
      "abusive_flag": false,
      "validation_status": "pending_implementation"
    },
    {
      "message": "I love your service!",
      "category": "Positive Feedback",
      "urgency": "Low",
      "urgency_reason": "Positive feedback does not require immediate action.",
      "sentiment": "Positive",
      "suggested_owner": "Customer Success",
      "draft_response": "Thank you so much! We appreciate your feedback.",
      "confidence": "High",
      "abusive_flag": false,
      "validation_status": "pending_implementation"
    }
  ]
}
```

**Batch Response Schema:**
```json
{
  "results": [
    {
      "message": "string",
      "category": "string or null",
      "urgency": "string or null",
      "urgency_reason": "string or null",
      "sentiment": "string or null",
      "suggested_owner": "string or null",
      "draft_response": "string or null",
      "confidence": "string or null",
      "abusive_flag": "boolean or null",
      "validation_status": "string or null",
      "error": "string or null"
    }
  ]
}
```

---

## JSON Request/Response Examples

### Example 1: Single High-Priority Issue

**Request:**
```json
{
  "message": "The system is down and I'm losing money every minute!"
}
```

**Response:**
```json
{
  "category": "Critical System Issue",
  "urgency": "Critical",
  "urgency_reason": "The customer reports a system outage causing financial losses.",
  "sentiment": "Angry",
  "suggested_owner": "Technical Support - Senior Engineer",
  "draft_response": "We understand the urgency. Our technical team is investigating immediately.",
  "confidence": "High",
  "abusive_flag": false,
  "validation_status": "pending_implementation"
}
```

### Example 2: Batch Processing Multiple Messages

**Request:**
```json
{
  "messages": [
    "My account has been locked for no reason",
    "When will the new feature be released?",
    "Thank you for the quick resolution!",
    "This product is garbage and doesn't work",
    "How do I upgrade my plan?"
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "message": "My account has been locked for no reason",
      "category": "Account Issue",
      "urgency": "High",
      "urgency_reason": "Account lock prevents customer access.",
      "sentiment": "Frustrated",
      "suggested_owner": "Account Management",
      "draft_response": "We will investigate the account lock immediately.",
      "confidence": "High",
      "abusive_flag": false,
      "validation_status": "pending_implementation"
    },
    {
      "message": "When will the new feature be released?",
      "category": "Feature Inquiry",
      "urgency": "Low",
      "urgency_reason": "General product inquiry.",
      "sentiment": "Neutral",
      "suggested_owner": "Product Management",
      "draft_response": "We'll share the release date once confirmed.",
      "confidence": "Medium",
      "abusive_flag": false,
      "validation_status": "pending_implementation"
    },
    {
      "message": "Thank you for the quick resolution!",
      "category": "Positive Feedback",
      "urgency": "Low",
      "urgency_reason": "Compliment does not require urgent handling.",
      "sentiment": "Positive",
      "suggested_owner": "Customer Success",
      "draft_response": "We're thrilled we could help!",
      "confidence": "High",
      "abusive_flag": false,
      "validation_status": "pending_implementation"
    },
    {
      "message": "This product is garbage and doesn't work",
      "category": "Complaint",
      "urgency": "High",
      "urgency_reason": "Strong negative feedback requires follow-up.",
      "sentiment": "Very Negative",
      "suggested_owner": "Customer Support - Senior Representative",
      "draft_response": "We're sorry you're unsatisfied. Let's discuss how we can help.",
      "confidence": "High",
      "abusive_flag": true,
      "validation_status": "pending_implementation"
    },
    {
      "message": "How do I upgrade my plan?",
      "category": "Billing",
      "urgency": "Low",
      "urgency_reason": "Standard upgrade request.",
      "sentiment": "Neutral",
      "suggested_owner": "Sales/Billing",
      "draft_response": "I'll guide you through the upgrade process.",
      "confidence": "High",
      "abusive_flag": false,
      "validation_status": "pending_implementation"
    }
  ]
}
```

---

## Error Responses

### 400 Bad Request

**Empty Message:**
```json
{
  "detail": "message field cannot be empty"
}
```

**Empty Batch:**
```json
{
  "detail": "messages array cannot be empty"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error - check logs for details"
}
```

---

## Integration Guide for Backend Developers

### 1. Setup & Installation

#### Local Development

```bash
# Clone the repository
git clone <repo-url>
cd customerReviews

# Create virtual environment
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r api/requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your LLM API keys and configuration
```

#### Docker Setup

```bash
# Build and start services
docker-compose build
docker-compose up

# API available at http://localhost:8000
# UI available at http://localhost:8501
```

### 2. Using the API Client

**Python Integration:**
```python
import requests

API_URL = "http://localhost:8000"

# Single message
response = requests.post(
    f"{API_URL}/triage",
    json={"message": "I need help with my account"}
)
result = response.json()

# Batch messages
messages = [
    "Help with billing",
    "Can't login",
    "Love your product"
]
response = requests.post(
    f"{API_URL}/triage/batch",
    json={"messages": messages}
)
results = response.json()["results"]
```

**JavaScript/Node.js Integration:**
```javascript
const API_URL = "http://localhost:8000";

// Single message
const singleResult = await fetch(`${API_URL}/triage`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message: "Help with billing" })
}).then(r => r.json());

// Batch messages
const batchResult = await fetch(`${API_URL}/triage/batch`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    messages: [
      "Help with billing",
      "Can't login",
      "Love your product"
    ]
  })
}).then(r => r.json());
```

### 3. Processing CSV/Excel Files

**Example: Process customer feedback from CSV:**
```python
import pandas as pd
import requests

# Read CSV
df = pd.read_csv("customer_feedback.csv")
messages = df["message"].tolist()

# Send to API
response = requests.post(
    "http://localhost:8000/triage/batch",
    json={"messages": messages}
)

# Parse results
results = response.json()["results"]

# Create output dataframe
output_df = pd.DataFrame(results)
output_df.to_csv("triage_results.csv", index=False)
```

### 4. Database Integration

Store triage results in your database:
```python
for result in results:
    db.session.add(TriageRecord(
        customer_message=result["message"],
        category=result["category"],
        urgency=result["urgency"],
        sentiment=result["sentiment"],
        suggested_owner=result["suggested_owner"],
        draft_response=result["draft_response"],
        confidence=result["confidence"],
        has_abusive_content=result["abusive_flag"]
    ))
db.session.commit()
```

### 5. Webhook Integration

Trigger downstream processes based on triage results:
```python
def process_triage_result(result):
    if result["urgency"] == "Critical":
        # Notify senior support team
        send_slack_notification(result)
    
    if result["abusive_flag"]:
        # Flag for moderation
        add_to_moderation_queue(result)
    
    # Route to appropriate department
    route_to_department(result["suggested_owner"], result)
```

---

## UI Features

### 1. Single Message Mode
- Enter a customer message in the text area
- Click "Send" to get instant triage
- Results displayed in a grid with all fields
- Theme toggle (Light/Dark) in sidebar

### 2. Batch Mode
- Upload CSV or Excel file (requires "message" column)
- Preview first 5 rows
- Click "Send" to process all messages
- Progress spinner shows processing status
- Download results as CSV

### 3. Theme Support
- Light mode (☀️) for daytime use
- Dark mode (🌙) for reduced eye strain
- Setting persists across page reloads

### 4. Status Indicators
- 📝 Shows single message ready status
- 📦 Shows batch message count ready for processing
- 🔄 Spinner during API processing
- ✅ Success confirmation
- ❌ Error messages with details

---

## API Rate Limiting & Performance

- Single message: ~1-3 seconds (depends on LLM)
- Batch processing: ~2-5 seconds per 10 messages
- Recommended batch size: Up to 100 messages per request
- No official rate limiting currently; implement as needed

---

## Troubleshooting

### API Connection Issues
```
Error: Connection refused
→ Ensure API is running: docker-compose up
→ Check API_URL environment variable
```

### Empty Results
```
Error: Empty message array or invalid format
→ Verify CSV/Excel has a "message" column
→ Check message values are non-empty strings
```

### Slow Processing
```
→ Reduce batch size
→ Check LLM API latency
→ Monitor API server resources
```

---

## Environment Variables

Create `.env` file in project root:

```env
# API Configuration
API_URL=http://backend:8000
API_PORT=8000

# LLM Configuration (if using OpenAI)
OPENAI_API_KEY=your_key_here
LLM_MODEL=gpt-4

# Database
DATABASE_URL=sqlite:///./app/data/triage.db

# UI Configuration
STREAMLIT_SERVER_PORT=8501
```

---

## Support & Maintenance

For issues or questions:
1. Check API logs: `docker-compose logs api`
2. Check UI logs: `docker-compose logs ui`
3. Review error messages in response `detail` field
4. Verify environment variables are set correctly

---

## Version History

- **v0.1.0** (Current)
  - Single message triage endpoint
  - Batch processing endpoint
  - Streamlit UI with theme support
  - Progress indicators and status display
  - CSV/Excel upload support
  - Results export functionality
