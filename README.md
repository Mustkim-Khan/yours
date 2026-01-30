<p align="center">
  <img src="https://img.shields.io/badge/🏥-Agentic%20AI%20Pharmacy-blueviolet?style=for-the-badge&labelColor=1a1a2e" alt="Agentic AI Pharmacy"/>
</p>

<h1 align="center">🏥 Agentic AI Pharmacy</h1>

<p align="center">
  <strong>An autonomous, multi-agent AI pharmacy system that revolutionizes medication management through conversational AI, real-time voice interaction, and intelligent automation.</strong>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"/></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.12+-green.svg" alt="Python 3.12+"/></a>
  <a href="https://nextjs.org"><img src="https://img.shields.io/badge/Next.js-14-black.svg" alt="Next.js 14"/></a>
  <a href="https://firebase.google.com"><img src="https://img.shields.io/badge/Firebase-Firestore-orange.svg" alt="Firebase"/></a>
  <a href="https://openai.com"><img src="https://img.shields.io/badge/OpenAI-GPT--4o-412991.svg" alt="OpenAI"/></a>
  <a href="https://langchain.com"><img src="https://img.shields.io/badge/LangChain-Enabled-1C3C3C.svg" alt="LangChain"/></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/AI-Multi--Agent-purple?style=for-the-badge" alt="AI Powered"/>
  <img src="https://img.shields.io/badge/Voice-Realtime-00D4AA?style=for-the-badge" alt="Realtime Voice"/>
  <img src="https://img.shields.io/badge/Vision-Enabled-FF6B6B?style=for-the-badge" alt="Vision Enabled"/>
</p>

---

## 🎯 Overview

**Agentic AI Pharmacy** is a cutting-edge healthcare solution that deploys specialized AI agents to autonomously handle the complete medication lifecycle. From natural language ordering to proactive refill reminders, our system provides a seamless, intelligent pharmacy experience.

### 🌟 Key Highlights

| Feature | Description |
|---------|-------------|
| 🎙️ **Realtime Voice AI** | Talk naturally with OpenAI's Realtime Voice API for hands-free ordering |
| 💬 **Natural Language Processing** | Order medicines using everyday language - text or voice |
| 🧠 **Contextual Memory** | Remembers your preferences, prescriptions, and order history |
| 📋 **Smart Prescription Validation** | AI vision validates prescriptions with GPT-4o Vision |
| 💊 **Medicine Cabinet** | Visual holographic cards to manage your medications |
| 🛒 **Smart Cart System** | Add, modify, and checkout with intelligent recommendations |
| ⏰ **Proactive Refill Alerts** | AI predicts when you'll need refills and reminds you |
| 📱 **WhatsApp Notifications** | Order confirmations delivered via Twilio |
| 🔒 **Secure & Isolated** | Per-user data isolation with Firebase Authentication |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Next.js 14 + TypeScript)                      │
│  ┌─────────┐ ┌──────────┐ ┌─────────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐  │
│  │ Landing │ │   Chat   │ │  Medicine   │ │  Cart   │ │  Orders  │ │  Admin  │  │
│  │  Page   │ │Interface │ │   Cabinet   │ │ Drawer  │ │  History │ │Dashboard│  │
│  └─────────┘ └──────────┘ └─────────────┘ └─────────┘ └──────────┘ └─────────┘  │
│                                     │                                            │
│       ┌─────────────────────────────┴─────────────────────────────┐              │
│       │           🎙️ Realtime Voice Interface (WebRTC)           │              │
│       └───────────────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             BACKEND (FastAPI + Python)                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐   │
│  │                       🎭 ORCHESTRATOR AGENT (GPT-4o)                      │   │
│  │           Central coordinator • Tool routing • Context management         │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                           │
│         ┌──────────────┬─────────────┼─────────────┬──────────────┐              │
│         ▼              ▼             ▼             ▼              ▼              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐      │
│  │💊Pharmacist│ │📦Inventory │ │📋 Policy   │ │🚚Fulfillment│ │⏰ Refill   │      │
│  │   Agent    │ │   Agent    │ │   Agent    │ │   Agent    │ │ Predictor  │      │
│  │  (GPT-4o)  │ │(GPT-4o-mini)│ │  (GPT-4o)  │ │(GPT-4o-mini)│ │(GPT-4o-mini)│     │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘      │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐   │
│  │                            🔧 SERVICES LAYER                              │   │
│  │  Cart Service • Medicine Explainer • Prescription Validator • Voice AI   │   │
│  │  Medicine Scanner • WhatsApp Service • Firestore Service • Data Services │   │
│  └───────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           ▼                          ▼                          ▼
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│  🔥 Firebase      │     │  📊 LangSmith     │     │  💬 Twilio        │
│    Firestore      │     │    Tracing        │     │   WhatsApp        │
└───────────────────┘     └───────────────────┘     └───────────────────┘
```

---

## 🤖 AI Agent Ecosystem

| Agent | Model | Responsibilities |
|-------|-------|------------------|
| **🎭 OrchestratorAgent** | GPT-4o | Central coordinator, intent classification, tool routing, context management |
| **💊 PharmacistAgent** | GPT-4o | Conversational interface, entity extraction, medicine recommendations, multilingual support |
| **📦 InventoryAgent** | GPT-4o-mini | Real-time stock checks, pricing, availability verification |
| **📋 PolicyAgent** | GPT-4o | Prescription validation, quantity limits, drug interaction checks, regulatory compliance |
| **🚚 FulfillmentAgent** | GPT-4o-mini | Order creation, confirmation, receipt generation, webhook triggers |
| **⏰ RefillPredictionAgent** | GPT-4o-mini | Proactive refill predictions, consumption analysis, reminder scheduling |

---

## ✨ Features

### 🎙️ Realtime Voice AI
- **Hands-free ordering** using OpenAI's Realtime Voice API
- Natural conversation flow with voice wave visualizations
- WebRTC-powered low-latency audio streaming
- Integrated with LangSmith for voice interaction tracing

### 💬 Conversational Commerce
- Natural language medicine ordering (text + voice)
- Multi-item order support with smart cart
- Context-aware responses across sessions
- Multilingual support (responds in user's language)

### 💊 Medicine Cabinet
- **Holographic card UI** for visual medication management
- Drug interaction web visualization
- Medicine explanation with AI-powered insights
- One-click reorder functionality

### 🛒 Smart Cart & Checkout
- Persistent cart with real-time updates
- Intelligent quantity recommendations
- Streamlined checkout flow
- Order confirmation celebrations

### 📋 Prescription Management
- **AI Vision validation** with GPT-4o
- Automatic extraction of doctor name, date, and medicines
- Expiration checking and reuse of valid prescriptions
- Secure image upload and processing

### 🔔 Proactive Notifications
- **Refill predictions** based on consumption patterns
- WhatsApp order confirmations via Twilio
- In-app notification center
- Smart reminder scheduling

### 📊 Observability & Admin
- **LangSmith tracing** for complete agent visibility
- Admin dashboard for monitoring and management
- Real-time analytics and order tracking
- Agent decision waterfall visualization

---

## 🛠️ Tech Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.128.0 | High-performance REST API framework |
| **Python** | 3.12+ | Backend runtime |
| **OpenAI** | 1.55.0+ | GPT-4o, GPT-4o-mini, Realtime Voice API |
| **LangChain** | 0.2.14+ | LLM orchestration and tool management |
| **LangSmith** | 0.1.101+ | Tracing, observability, and debugging |
| **Firebase Admin** | Latest | Firestore database integration |
| **Twilio** | 9.3.2 | WhatsApp notification delivery |
| **WebRTC** | Native | Realtime voice streaming |

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| **Next.js** | 14.1.0 | React framework with App Router |
| **TypeScript** | 5.x | Type-safe development |
| **TailwindCSS** | 3.3.0 | Utility-first styling |
| **Firebase** | 12.8.0 | Authentication & Firestore client |
| **Framer Motion** | 11.0.8 | Smooth animations and transitions |
| **Lucide React** | 0.312.0 | Modern icon library |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+
- Firebase project with Firestore enabled
- OpenAI API key (with access to GPT-4o and Realtime API)
- (Optional) Twilio account for WhatsApp notifications

### 🔧 Backend Setup

```bash
# Clone the repository
git clone https://github.com/Mustkim-Khan/yours.git
cd yours/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

**Required Environment Variables:**
```env
# OpenAI
OPENAI_API_KEY=sk-...

# LangSmith (Observability)
LANGSMITH_API_KEY=ls-...
LANGSMITH_PROJECT=agentic-ai-pharmacy

# Firebase
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json

# Optional: WhatsApp Notifications
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

**Start the backend:**
```bash
python main.py
# 🚀 Server runs at http://localhost:8000
```

### 🎨 Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env.local
```

**Required Environment Variables:**
```env
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=...
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
```

**Start the development server:**
```bash
npm run dev
# 🎨 App runs at http://localhost:3000
```

---

## 📁 Project Structure

```
yours/
├── 🔙 backend/
│   ├── agents/                     # AI Agent implementations
│   │   ├── orchestrator_agent.py   # Central coordinator
│   │   ├── pharmacist_agent.py     # Conversational AI
│   │   ├── inventory_agent.py      # Stock management
│   │   ├── policy_agent.py         # Compliance & validation
│   │   ├── fulfillment_agent.py    # Order processing
│   │   └── refill_prediction_agent.py
│   │
│   ├── services/                   # Business logic layer
│   │   ├── cart_service.py         # Cart operations
│   │   ├── data_services.py        # Firestore data access
│   │   ├── medicine_explainer.py   # AI medicine explanations
│   │   ├── medicine_scanner_service.py  # Pill identification
│   │   ├── prescription_validator.py    # Vision-based validation
│   │   ├── realtime_voice_service.py    # Voice AI service
│   │   └── whatsapp_service.py     # Twilio integration
│   │
│   ├── models/                     # Pydantic schemas
│   ├── utils/                      # Helpers & tracing
│   ├── main.py                     # FastAPI application
│   └── requirements.txt
│
├── 🎨 frontend/
│   ├── app/                        # Next.js App Router
│   │   ├── page.tsx                # Main chat interface
│   │   ├── landing/                # Marketing landing page
│   │   ├── cabinet/                # Medicine cabinet
│   │   ├── orders/                 # Order history
│   │   ├── admin/                  # Admin dashboard
│   │   └── login/                  # Authentication
│   │
│   ├── components/                 # React components
│   │   ├── ui/                     # UI component library
│   │   │   ├── RealtimeVoiceButton.tsx
│   │   │   ├── HolographicCard.tsx
│   │   │   ├── InteractionWeb.tsx
│   │   │   ├── VoiceWave.tsx
│   │   │   └── OrderCelebration.tsx
│   │   ├── landing/                # Landing page components
│   │   ├── CartDrawer.tsx
│   │   ├── CheckoutModal.tsx
│   │   ├── ExplainMedicineCard.tsx
│   │   └── ...
│   │
│   ├── lib/                        # Utilities & services
│   │   ├── firestoreService.ts
│   │   ├── cabinetService.ts
│   │   └── useRealtimeVoice.ts
│   │
│   └── package.json
│
└── README.md
```

---

## 🎬 Demo Scenarios

### 💬 Natural Language Ordering
```
👤 User: "I need 10 paracetamol tablets"
🤖 AI: [Shows order preview card with 10 tablets, ₹25]
👤 User: "Confirm"
🤖 AI: ✅ Order confirmed! Receipt #ORD-12345
📱 WhatsApp: Order notification sent!
```

### 📋 Prescription Medicine Flow
```
👤 User: "I want Metformin 500mg"
🤖 AI: "Metformin requires a valid prescription. Please upload."
👤 User: [Uploads prescription image]
🤖 AI: [GPT-4o Vision validates prescription]
🤖 AI: "✅ Prescription verified! Dr. Sharma, dated 2026-01-20, valid for 6 months"
🤖 AI: [Shows order preview]
```

### 🎙️ Voice Ordering
```
👤 User: [Clicks microphone] "I need blood pressure medicine"
🤖 AI: [Voice response] "I found Amlodipine 5mg in stock. Would you like to add it?"
👤 User: "Yes, add 30 tablets"
🤖 AI: [Voice] "Added to your cart! Anything else?"
```

### ⏰ Proactive Refill
```
🤖 AI: "⏰ Your Paracetamol supply (30 tablets) ends in 3 days based on 
       your usual consumption. Would you like to refill?"
👤 User: "Yes, same quantity"
🤖 AI: [Shows refill order preview for 30 tablets]
```

---

## 📊 Performance Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| **Conversation Persistence** | ~95% | Full context restoration across sessions |
| **Order Intent Accuracy** | ~90% | Correct medicine and quantity extraction |
| **Entity Extraction** | ~90% | Name, dosage, quantity identification |
| **Policy Enforcement** | ~95% | Prescription and limit compliance |
| **End-to-End Automation** | ~85% | Orders completed without intervention |
| **Voice Recognition** | ~92% | Accurate voice-to-text conversion |

---

## 🔒 Security & Compliance

- 🔐 **Firebase Authentication** for secure user identity
- 🔒 **Per-user data isolation** in Firestore
- 📋 **Prescription validation** prevents unauthorized controlled substance orders
- 🛡️ **No sensitive data** logged in traces (PHI compliant)
- 🔑 **API key encryption** for all third-party services

---

## 🗺️ Roadmap

- [ ] 🏥 Multi-pharmacy network support
- [ ] 💳 Insurance integration & claims processing
- [ ] 🧬 Advanced drug interaction AI with genomic data
- [ ] 📡 IoT smart pill dispenser integration
- [ ] 👨‍⚕️ Telemedicine integration for consultations
- [ ] 📱 Native mobile apps (iOS/Android)
- [ ] 🌍 Multi-language voice support

---

## 👥 Contributors

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/Mustkim-Khan">
        <strong>Mustkim Khan</strong>
      </a>
      <br />
      <sub>Full Stack Developer</sub>
    </td>
  </tr>
</table>

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **OpenAI** - GPT-4o, GPT-4o-mini, and Realtime Voice API
- **LangChain & LangSmith** - LLM orchestration and observability
- **Firebase** - Authentication and Firestore database
- **Twilio** - WhatsApp API integration
- **Vercel** - Next.js framework and hosting

---

<p align="center">
  <img src="https://img.shields.io/badge/Built%20with-❤️-red?style=for-the-badge" alt="Built with love"/>
</p>

<p align="center">
  <strong>🏥 Revolutionizing Healthcare with AI 🏥</strong>
  <br/>
  <sub>Built for the future of intelligent pharmacy management</sub>
</p>
