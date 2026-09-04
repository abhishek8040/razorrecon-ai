# RazorRecon AI

**Razorpay Buildathon 2026 — Track 04: AI Finance Controller**

RazorRecon AI is a full-stack, AI-assisted financial reconciliation controller designed specifically to solve the "Truth vs. AI" dilemma in fintech. 

In financial systems, deterministic accuracy is paramount. AI cannot be trusted to independently alter financial records or invent "truths." RazorRecon AI solves this by keeping a **strict boundary between deterministic logic and AI investigation**. The core reconciliation engine runs deterministically, while the AI acts purely as an investigator for ambiguous exceptions, subject to strict audit trails and human oversight.

---

## 🚀 Key Features

*   **Deterministic Core Engine**: Exact matching and policy-based auto-resolution (e.g., standard fee tolerance) are handled by a deterministic Python engine.
*   **AI Investigator**: When an ambiguous exception occurs (e.g., missing settlement, abnormal amount mismatch), the system escalates it. The Gemini AI agent then investigates the candidates and provides a structured JSON recommendation (MATCH, REVIEW, UNRESOLVED).
*   **Data Ingestion UI**: Upload custom CSVs for Payments, Settlements, and Bank Transactions directly through the dashboard.
*   **Finance Q&A Assistant**: A conversational AI interface grounded in live reconciliation data that allows you to query your metrics and exception statuses.
*   **Immutable Audit Ledger**: Every system action, policy auto-resolution, and AI recommendation is deterministically logged with reason codes.
*   **Evaluation Engine**: Built-in benchmarking against held-out datasets to accurately measure Precision, Recall, and Auto-Match rates.

---

## 🏗️ Architecture

*   **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS, Recharts, Lucide Icons.
*   **Backend:** Python 3, FastAPI, SQLModel (SQLAlchemy).
*   **AI Integration:** Google GenAI SDK (`gemini-2.5-flash`), leveraging strict `response_schema` structured outputs.
*   **Database:** SQLite (for zero-dependency local development). Ready to switch to PostgreSQL via connection string.

---

## 💻 How to Run Locally

### 1. Backend Setup

Open a terminal and navigate to the `backend` directory:

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure Environment Variables
# Edit the .env file in the backend directory and add your Gemini API Key:
# AI_PROVIDER=gemini
# GEMINI_API_KEY=your_google_api_key
# DATABASE_URL=sqlite:///./razorrecon.db

# Seed the database with 1,500 synthetic records
python app/cli.py seed:db

# Start the FastAPI Server
uvicorn app.main:app --reload --port 8000
```
The backend API will be running at `http://127.0.0.1:8000` (interactive docs available at `/docs`).

### 2. Frontend Setup

Open a second terminal window and navigate to the `frontend` directory:

```bash
cd frontend

# Install Node modules
npm install

# Start the Next.js development server
npm run dev
```
The dashboard will be accessible at **[http://localhost:3000](http://localhost:3000)**.

---

## 🧪 Testing the Workflow

1. **Dashboard Overview:** Navigate to `http://localhost:3000` to see your initial metrics.
2. **Run Reconciliation:** Go to the **Reconciliation** tab and click **Start Run**. The deterministic engine will match all records.
3. **AI Investigation:** Go to the **Exceptions** tab. Select an unresolved exception and click **Run Investigation**. Gemini will analyze the discrepancy and output a recommended action.
4. **Data Upload:** Go to the **Data Ingestion** tab to upload your own `payments.csv` or `settlements.csv` (demo files are available in `backend/data/demo/`).
5. **Q&A Chat:** Go to the **Finance Q&A** tab and ask the AI a question about your current metrics.

---
*Built for the Razorpay Buildathon 2026*
