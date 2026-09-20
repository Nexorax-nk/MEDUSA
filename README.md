# 🐍 MEDUSA 
**Medical Emergency Dispatch & Universal Support Agent**

![MEDUSA Banner](https://img.shields.io/badge/Status-Live-success?style=for-the-badge) ![AWS](https://img.shields.io/badge/AWS-%23FF9900.svg?style=for-the-badge&logo=amazon-aws&logoColor=white) ![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB) ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)

## 🚨 The Problem: Losing the "Golden Hour"
In rural and underserved areas, medical emergencies often lead to a frantic rush to the *nearest* hospital. However, if that facility is poorly equipped or lacks the required specialist (e.g., a neurologist for a stroke, or a cardiologist for a heart attack), the patient must be transferred again. 

This tragic delay wastes the **"Golden Hour"**—the critical 60-minute window following a traumatic injury or medical event where prompt medical intervention yields the highest chance of survival.

## 💡 Our Solution
**MEDUSA** is an autonomous, voice-driven AI Command Center that completely eliminates the guesswork in emergency response. 

The moment a crisis is reported, MEDUSA's AI agents instantly:
1. **Identify the Patient:** Fetch medical history, known conditions, and blood type from secure memory.
2. **Triages the Situation:** Analyzes symptoms to determine clinical severity.
3. **Discovers Resources:** Searches real-time databases to find the *right* hospital with the *exact* specialists required.
4. **Executes Logistics:** Automatically dispatches transport, notifies family members, and transmits clinical handoff documents to the receiving hospital before the patient even arrives.

---

## ⚙️ Technical Architecture

### 🧠 Agentic Architecture & MCP Server
At the core of MEDUSA is a **Multi-Agent System** powered by a custom **Model Context Protocol (MCP) Server**. This architecture allows our LLM reasoning engines to interface dynamically with the physical world. 

The backend exposes exactly **21 Specialized Tools** to the Agent, divided across distinct operational domains:
- **Patient Context:** Resolving kinship, fetching medical history, allergy alerts.
- **Situation Triage:** Assigning clinical priority, parsing symptoms.
- **Resource Discovery:** Validating hospital capacity and specialist availability via SerpAPI.
- **Communication:** Triggering AWS SNS alerts for family members.
- **Transport & Handoff:** Generating clinical handoff documents and requesting ambulances.

By utilizing **HTTP Server-Sent Events (SSE)**, the frontend receives a real-time, streamable narrative of the agent's thought process. This provides human operators with split-second visibility into the AI's execution pipeline as it makes life-saving decisions.

### 🏗️ Cloud Infrastructure
MEDUSA is built on a highly scalable, event-driven cloud architecture:
- **Frontend:** React + TypeScript (Vite), deployed globally on **AWS Amplify**.
- **Backend:** FastAPI + Python (Uvicorn), deployed on **Render** for high-availability compute.
- **Database:** **Amazon DynamoDB** for sub-millisecond memory and incident state tracking.
- **Event Bus:** **Amazon EventBridge** for asynchronous emergency escalations.
- **Notifications:** **Amazon SNS** for automated SMS/Email family alerts.
- **Observability:** **Amazon CloudWatch** for agent activity logging and metric tracking.
- **External APIs:** **SerpAPI** for real-time facility mapping and routing.

---

## 🚀 Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Nexorax-nk/MEDUSA.git
cd MEDUSA
```

### 2. Backend Setup (FastAPI)
```bash
cd backend
python -m venv venv
# On Windows: venv\Scripts\activate
# On Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:
```env
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_DEFAULT_REGION=us-east-1

GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
SERPAPI_API_KEY=your_serpapi_key
```

Run the server:
```bash
uvicorn server:app --reload
```

### 3. Frontend Setup (React)
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

*Built with ❤️ for the Hackathon. Saving lives, one millisecond at a time.*
