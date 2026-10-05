# 🛒 Gemini Assistant for a Better Shopping Experience

An AI-powered shopping assistant backend built with **FastAPI** and **Google Gemini AI**. This system understands natural language shopping queries, provides intelligent product recommendations, and delivers interactive responses with tutorials and troubleshooting guides.

![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.142-green.svg)
![Gemini](https://img.shields.io/badge/Gemini-AI-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [Connecting Your Data](#-connecting-your-data)
- [Deployment](#-deployment)
- [Contributing](#-contributing)

---

## 🎯 Overview

This backend powers an intelligent shopping assistant that can:

- **Understand Intent**: Recognizes what the user wants (search, compare, recommend, troubleshoot)
- **Extract Entities**: Identifies products, prices, brands, and features from natural language
- **Maintain Context**: Remembers conversation history for multi-turn interactions
- **Provide Rich Responses**: Returns products, comparisons, and tutorial videos

### Example Interactions

```
User: "I need a laptop for programming under $2000"
→ AI identifies: Intent=PRODUCT_SEARCH, Category=laptops, MaxPrice=$2000
→ Returns: Filtered products + personalized message

User: "Compare the top two"
→ AI uses context to know which products to compare
→ Returns: Side-by-side comparison table

User: "My laptop won't turn on"
→ AI identifies: Intent=TROUBLESHOOT
→ Returns: Troubleshooting steps + tutorial video
```

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT (Mobile/Web App)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        LAYER 1: API GATEWAY                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────┐ │
│  │   REST API       │  │   WebSocket      │  │   Rate Limiting        │ │
│  │   /api/v1/*      │  │   /chat/ws       │  │   CORS Middleware      │ │
│  └──────────────────┘  └──────────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       LAYER 2: AI ENGINE                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │
│  │   Intent    │  │   Entity    │  │   Context   │  │   Response     │  │
│  │ Classifier  │  │  Extractor  │  │   Manager   │  │   Generator    │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────────┘  │
│         │                │                │                 │            │
│         └────────────────┴────────────────┴─────────────────┘            │
│                                    │                                     │
│                          ┌─────────────────┐                             │
│                          │   Gemini API    │                             │
│                          │   (Google AI)   │                             │
│                          └─────────────────┘                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      LAYER 3: SERVICES                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────┐ │
│  │  Product Service │  │  Media Service   │  │  Context Manager       │ │
│  │  Search/Compare  │  │  Tutorials/Videos│  │  Session Persistence   │ │
│  └──────────────────┘  └──────────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       LAYER 4: DATA                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────┐ │
│  │     SQLite       │  │  Connection Pool │  │   In-Memory Cache      │ │
│  │    Database      │  │   (50 conns)     │  │   (Session State)      │ │
│  └──────────────────┘  └──────────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI-Powered Chat** | Natural language understanding with Gemini AI |
| 🔍 **Smart Search** | Full-text search with filters (price, category, brand) |
| ⚖️ **Product Comparison** | Side-by-side comparison of 2-4 products |
| 💡 **Recommendations** | Personalized suggestions based on preferences |
| 🛠 **Troubleshooting** | Issue resolution with tutorial videos |
| 💬 **Multi-turn Context** | Remembers conversation history |
| ⚡ **High Concurrency** | Async architecture, connection pooling |
| 🔒 **Rate Limiting** | Configurable API rate limits |
| 📊 **Structured Logging** | JSON logs for production monitoring |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Gemini API Key ([Get one free](https://makersuite.google.com/app/apikey))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/ShreyashDarade/Gemini_Assistant-for-a-Better-Shopping-Experience.git
cd Gemini_Assistant-for-a-Better-Shopping-Experience

# 2. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
```

### Configuration

Edit `.env` file with your settings:

```env
# Required: Your Gemini API Key
GEMINI_API_KEY=your_actual_api_key_here

# Optional: Model configuration
AI_MODEL=gemini-3-pro-preview
AI_MAX_TOKENS=2048
AI_TEMPERATURE=0.7
```

### Run the Server

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Verify Installation

Open your browser and navigate to:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Detailed Health**: http://localhost:8000/health/detailed

---

## 📚 API Reference

### Chat Endpoints

#### POST `/api/v1/chat`
Send a message and receive AI response.

**Headers:**
| Header | Description | Required |
|--------|-------------|----------|
| `X-Session-ID` | Session ID for conversation continuity | No |
| `X-User-ID` | User identifier for personalization | No |

**Request Body:**
```json
{
  "message": "I need a laptop for programming under $2000"
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "I found some great laptops for programming within your budget!",
  "intent": "product_search",
  "intent_confidence": 0.95,
  "products": [
    {
      "id": 1,
      "name": "MacBook Pro 14-inch",
      "brand": "Apple",
      "price": 1999.00,
      "rating": 4.8,
      "in_stock": true
    }
  ],
  "suggestions": ["Compare products", "Filter by brand"],
  "processing_time_ms": 450
}
```

#### WebSocket `/api/v1/chat/ws`
Real-time bidirectional chat.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/chat/ws?session_id=xxx');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.message);
};

ws.send(JSON.stringify({ message: "Show me laptops" }));
```

---

### Product Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/products` | Search products with filters |
| GET | `/api/v1/products/{id}` | Get product details |
| GET | `/api/v1/products/{id}/similar` | Get similar products |
| POST | `/api/v1/products/compare` | Compare 2-4 products |
| GET | `/api/v1/products/categories` | List all categories |
| GET | `/api/v1/products/brands` | List all brands |

**Search Parameters:**
```
GET /api/v1/products?category=laptops&min_price=500&max_price=2000&sort_by=rating
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Free-text search |
| `category` | string | Filter by category |
| `brand` | string | Filter by brand |
| `min_price` | number | Minimum price |
| `max_price` | number | Maximum price |
| `min_rating` | number | Minimum rating (0-5) |
| `in_stock_only` | boolean | Only in-stock items |
| `sort_by` | string | `relevance`, `price_asc`, `price_desc`, `rating`, `newest` |
| `page` | number | Page number |
| `page_size` | number | Results per page (max 50) |

---

### Media Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/media` | Search media assets |
| GET | `/api/v1/media/{id}` | Get media details |
| GET | `/api/v1/media/tutorials` | Find tutorials |
| GET | `/api/v1/media/product/{id}` | Get product media |

---

## ⚙️ Configuration

All configuration is done through environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | **Required.** Google Gemini API key | - |
| `AI_MODEL` | Gemini model name | `gemini-3-pro-preview` |
| `AI_MAX_TOKENS` | Max tokens per response | `2048` |
| `AI_TEMPERATURE` | Response creativity (0-1) | `0.7` |
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./shopping_assistant.db` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `WORKERS` | Number of worker processes | `4` |
| `DEBUG` | Enable debug mode | `false` |
| `CORS_ORIGINS` | Allowed CORS origins | `["*"]` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `60` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FORMAT` | Log format (`json` or `text`) | `json` |

---

## 📁 Project Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   │
│   ├── models/                 # Database models (SQLAlchemy)
│   │   ├── database.py         # DB connection & pooling
│   │   ├── product.py          # Product model
│   │   ├── conversation.py     # Conversation & Message models
│   │   └── media.py            # Media content model
│   │
│   ├── schemas/                # Pydantic schemas (validation)
│   │   ├── chat.py             # Chat request/response schemas
│   │   ├── product.py          # Product schemas
│   │   └── media.py            # Media schemas
│   │
│   ├── services/               # Business logic
│   │   ├── ai_engine.py        # Main AI orchestrator
│   │   ├── gemini_client.py    # Gemini API wrapper
│   │   ├── intent_classifier.py # Intent classification
│   │   ├── entity_extractor.py # Entity extraction
│   │   ├── context_manager.py  # Conversation context
│   │   ├── response_generator.py # Response generation
│   │   ├── product_service.py  # Product operations
│   │   └── media_service.py    # Media operations
│   │
│   ├── routers/                # API endpoints
│   │   ├── chat.py             # Chat endpoints
│   │   ├── products.py         # Product endpoints
│   │   ├── media.py            # Media endpoints
│   │   └── health.py           # Health checks
│   │
│   └── utils/
│       └── seed_data.py        # Data seeding utility
│
├── .env.example                # Environment template
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Test configuration
└── README.md                   # This file
```

---

## 🧠 How It Works

### 1. Intent Classification

When a user sends a message, the AI classifies it into one of these intents:

| Intent | Description | Example |
|--------|-------------|---------|
| `product_search` | Find products | "Show me laptops under $1000" |
| `product_compare` | Compare items | "Compare iPhone vs Samsung" |
| `product_recommend` | Get suggestions | "What phone should I buy?" |
| `troubleshoot` | Get help | "My laptop won't start" |
| `greeting` | User greeting | "Hi there!" |
| `farewell` | User goodbye | "Thanks, bye!" |
| `general_query` | Other questions | "What's your return policy?" |

### 2. Entity Extraction

The AI extracts structured data from natural language:

```
Input: "Show me Nike running shoes under $150 in red"

Extracted:
- brand: "Nike"
- category: "shoes"
- subcategory: "running"
- max_price: 150
- color: "red"
```

### 3. Context Management

The system maintains conversation context:

- **Session persistence**: Conversations stored in database
- **In-memory cache**: Fast access to recent sessions
- **Preference tracking**: Remembers user preferences
- **Product history**: Tracks discussed products

### 4. Response Generation

Based on intent and context, the AI generates:

- **Text response**: Natural language reply
- **Products**: Relevant product list
- **Media**: Tutorial videos for troubleshooting
- **Suggestions**: Follow-up action buttons

---

## 🔌 Connecting Your Data

The system comes with no sample data. To connect your products:

### Option 1: Direct Database Insertion

```python
from app.models.product import Product
from app.models.database import get_db_context


async def add_products():
    async with get_db_context() as db:
        product = Product(
            name="Your Product",
            description="Product description",
            category="electronics",
            brand="Brand",
            price=99.99,
            stock=100,
            rating=4.5,
        )
        db.add(product)
        await db.commit()
```

### Option 2: Modify Seed Script

Edit `app/utils/seed_data.py`:

```python
async def seed_sample_data():
    # Fetch from your API
    products = await your_api.get_products()

    # Convert to Product model format
    product_data = [
        {
            "name": p["title"],
            "description": p["desc"],
            "category": p["cat"],
            "brand": p["brand"],
            "price": p["price"],
            "stock": p["inventory"],
            "image_url": p["image"],
        }
        for p in products
    ]

    await seed_from_external_source(product_data)
```

### Option 3: REST API

Create products via API (add endpoint if needed):

```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Product Name",
    "description": "Description",
    "category": "electronics",
    "brand": "Brand",
    "price": 99.99,
    "stock": 100
  }'
```

---

## 🚢 Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t shopping-assistant .
docker run -p 8000:8000 --env-file .env shopping-assistant
```

### Google Cloud Run

```bash
gcloud run deploy shopping-assistant \
  --source . \
  --set-env-vars GEMINI_API_KEY=your_key
```

### Production Considerations

1. **Use PostgreSQL** instead of SQLite for production
2. **Set DEBUG=false** in production
3. **Configure proper CORS_ORIGINS** (not `["*"]`)
4. **Use a reverse proxy** (Nginx) for SSL termination
5. **Monitor with** structured JSON logs

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI language model
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database toolkit

---

**Built with ❤️ for a better shopping experience**


---

## 🚀 Modern Tooling & Production Notes (v2)

- **Stack**: Python 3.13, FastAPI 0.142, SQLAlchemy 2.1 (async), Pydantic 2.13, official `google-genai` SDK (native async, system instructions, JSON mode), managed with [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`).
- **Run locally**: `uv sync && cp .env.example .env && uv run uvicorn app.main:app --reload`
- **Quality**: `uv run ruff check . && uv run ruff format --check . && uv run pytest` (also run in CI).
- **Docker**: `docker build -t shopping-assistant .` (multi-stage, non-root, healthcheck). `docker compose up` runs the API against Postgres 17 (set `POSTGRES_PASSWORD`).
- **Observability**: structured JSON logs with `X-Request-ID` correlation, Prometheus metrics at `/metrics`, `/live`, `/ready` (503 when the DB is down) and `/health/detailed`.
- **Resilience**: bounded Gemini concurrency, request timeout, retries with jittered backoff on transient errors only, per-IP rate limiting, graceful shutdown.
- **No authentication** is built in by design; put the service behind your gateway/network controls and set `CORS_ORIGINS` to your real origins in production.
- Default model is `gemini-2.5-flash` (GA); set `AI_MODEL` to use another.
