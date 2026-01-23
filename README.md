# 🏥 Agentic AI Pharmacy

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-green.svg)](https://python.org)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore-orange.svg)](https://firebase.google.com)

> **An autonomous, multi-agent AI pharmacy system that manages the complete medication lifecycle - from natural language ordering to proactive refill reminders.**

![Agentic AI Pharmacy](https://img.shields.io/badge/AI-Powered-purple?style=for-the-badge)

---

## 🎯 Overview

Agentic AI Pharmacy revolutionizes medication management by deploying specialized AI agents that autonomously handle:

- 💬 **Natural Language Ordering** - Text or voice, just speak naturally
- 🧠 **Contextual Memory** - Remembers your medicines, quantities, and history
- 📋 **Smart Prescription Validation** - AI vision validates prescriptions with GPT-5.2
- ⏰ **Proactive Refill Alerts** - Predicts when you'll need refills
- 📱 **WhatsApp Notifications** - Order confirmations via Twilio
- 🔒 **Per-User Isolation** - Secure, persistent conversations per user

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 14)                        │
│   Chat UI │ Order Cards │ Prescription Upload │ Admin Dashboard     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   🎭 ORCHESTRATOR AGENT                      │   │
│  │              Central coordinator for all agents              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│         ┌────────────────────┼────────────────────┐                │
│         ▼                    ▼                    ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│  │💊 Pharmacist │    │📦 Inventory  │    │📋 Policy     │         │
│  │    Agent     │    │    Agent     │    │    Agent     │         │
│  │  (GPT-5.2)   │    │ (GPT-5-mini) │    │  (GPT-5.2)   │         │
│  └──────────────┘    └──────────────┘    └──────────────┘         │
│         │                    │                    │                │
│         └────────────────────┼────────────────────┘                │
│                              ▼                                      │
│  ┌──────────────┐    ┌──────────────┐                              │
│  │🚚 Fulfillment│    │⏰ Refill     │                              │
│  │    Agent     │    │  Prediction  │                              │
│  │ (GPT-5-mini) │    │ (GPT-5-mini) │                              │
│  └──────────────┘    └──────────────┘                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FIREBASE FIRESTORE                               │
│        Conversations │ Orders │ Users │ Refill Alerts              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 AI Agents

| Agent | Model | Purpose |
|-------|-------|---------|
| **OrchestratorAgent** | GPT-5.2 | Central coordinator, routes requests to specialized agents |
| **PharmacistAgent** | GPT-5.2 | Conversational interface, entity extraction, order intent |
| **InventoryAgent** | GPT-5-mini | Stock checks, pricing, availability |
| **PolicyAgent** | GPT-5.2 | Prescription validation, quantity limits, drug interactions |
| **FulfillmentAgent** | GPT-5-mini | Order creation, confirmation, receipts |
| **RefillPredictionAgent** | GPT-5-mini | Proactive refill predictions and reminders |

---

## ✨ Features

### Core Features
- ✅ Natural language medicine ordering (text + voice)
- ✅ Multi-item order support
- ✅ Real-time order preview cards
- ✅ Prescription upload with AI validation
- ✅ Drug interaction checks
- ✅ Quantity limit enforcement

### Persistence & Memory
- ✅ Conversation history stored in Firestore
- ✅ Per-user data isolation
- ✅ Context memory across sessions
- ✅ Order history persistence

### Notifications
- ✅ WhatsApp order confirmations (Twilio)
- ✅ Proactive refill reminders
- ✅ In-app notification alerts

### Observability
- ✅ LangSmith tracing integration
- ✅ Agent decision waterfall visibility
- ✅ Admin dashboard for monitoring

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.128.0 | REST API framework |
| Python | 3.12+ | Backend language |
| OpenAI | 1.55.0 | GPT-5.2 / GPT-5-mini models |
| LangChain | 0.2.14 | LLM orchestration |
| LangSmith | 0.1.101 | Tracing & observability |
| Firebase Admin | - | Firestore integration |
| Twilio | 9.3.2 | WhatsApp notifications |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 14.1.0 | React framework |
| TypeScript | 5.x | Type-safe JavaScript |
| TailwindCSS | 3.3.0 | Utility-first CSS |
| Firebase | 12.8.0 | Auth & Firestore |
| Framer Motion | 11.0.8 | Animations |
| Lucide React | 0.312.0 | Icons |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+
- Firebase project with Firestore enabled
- OpenAI API key
- (Optional) Twilio account for WhatsApp

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/Mustkim-Khan/yours.git
cd yours/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

**Required Environment Variables:**
```env
OPENAI_API_KEY=sk-...
LANGSMITH_API_KEY=ls-...
LANGSMITH_PROJECT=agentic-ai-pharmacy
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json

# Optional: WhatsApp notifications
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

**Start the backend:**
```bash
python main.py
# Server runs at http://localhost:8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env.local
# Edit .env.local with your Firebase config

# Start development server
npm run dev
# App runs at http://localhost:3000
```

**Required Environment Variables:**
```env
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
```

---

## 📁 Project Structure

```
yours/
├── backend/
│   ├── agents/                 # AI Agents
│   │   ├── orchestrator_agent.py
│   │   ├── pharmacist_agent.py
│   │   ├── inventory_agent.py
│   │   ├── policy_agent.py
│   │   ├── fulfillment_agent.py
│   │   └── refill_prediction_agent.py
│   ├── services/               # Business logic
│   │   ├── data_services.py
│   │   ├── firestore_service.py
│   │   ├── prescription_validator.py
│   │   └── whatsapp_service.py
│   ├── models/                 # Pydantic schemas
│   ├── utils/                  # Helpers & tracing
│   ├── main.py                 # FastAPI app
│   └── requirements.txt
│
├── frontend/
│   ├── app/                    # Next.js pages
│   │   ├── page.tsx            # Main chat interface
│   │   ├── admin/              # Admin dashboard
│   │   └── login/              # Authentication
│   ├── components/             # React components
│   │   ├── PrescriptionUploadCard.tsx
│   │   ├── OrderPreviewCard.tsx
│   │   └── ...
│   ├── lib/                    # Firebase services
│   └── package.json
│
└── README.md
```

---

## 🎬 Demo Flow

### 1. Natural Ordering
```
User: "I need 10 paracetamol tablets"
AI: Shows order preview card with 10 tablets
User: "Confirm"
AI: Order confirmed! WhatsApp notification sent.
```

### 2. Prescription Medicine
```
User: "I want Metformin"
AI: "Metformin requires a prescription. Please upload."
User: [Uploads prescription image]
AI: [Validates with GPT-5.2 Vision]
AI: "✅ Prescription verified! Dr. Sharma, dated 2026-01-20"
AI: Shows order preview
```

### 3. Proactive Refills
```
AI: "⏰ Your Paracetamol supply ends in 3 days. Would you like to refill?"
User: "Yes"
AI: Shows refill order preview
```

---

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| Conversation Persistence | ~95% |
| Order Intent Accuracy | ~90% |
| Entity Extraction Confidence | ~90% |
| Safety/Policy Enforcement | ~95% |
| End-to-End Automation | ~85% |

---

## 🔒 Security

- Firebase Authentication for user identity
- Per-user data isolation in Firestore
- Prescription validation prevents unauthorized medicine orders
- No sensitive data logged in traces

---

## 🗺️ Roadmap

- [ ] Multi-pharmacy network support
- [ ] Insurance integration
- [ ] Advanced drug interaction AI
- [ ] IoT pill dispenser integration
- [ ] Telemedicine integration

---

## 👥 Contributors

- **Mustkim Khan** - Full Stack Developer

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- OpenAI for GPT models
- LangChain & LangSmith for LLM infrastructure
- Firebase for backend services
- Twilio for WhatsApp API

---

<p align="center">
  Built with ❤️ for the future of healthcare AI
</p>
