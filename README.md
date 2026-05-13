# SQL Agent — Intelligent AI SQL Data Analyst with Human-in-the-Loop & Visualization

## 💡 Overview
**SQL Agent** is an **AI-powered data analysis orchestrator** that understands natural language queries, decides whether to execute SQL or visualize results, ensures database safety through **human approval**, and generates **instant visual insights** — all powered by an intelligent **LangGraph agent system**.

It integrates **LangChain**, **LangGraph**, **GPT-4.1**, **FastAPI**, and deployed on **Render** using **Docker**.

---
## ⚙️ Features

### 🧭 1. Automatic Query Routing
- Dynamically decides whether a user query requires:
  - 🧠 **SQL Execution** — query the connected database
  - 📊 **Data Visualization** — generate a chart from previous results
  - 💬 **General LLM Response** — answer using AI + live web search
- Uses **Pydantic Output Parsers** for structured, reliable decision-making.

---

### 🗄️ 2. Database Connection Validation
- Validates the database connection before executing any query.
- Supports **SQLite, PostgreSQL, MySQL** via connection URI.
- Each user gets an **isolated database** — your data stays private.
- Notifies the user immediately if the connection is missing or invalid.

---

### 🛡️ 3. SQL Query Safety Analyzer
- Classifies every query as **safe** or **dangerous**.
- Flags destructive operations: `DELETE`, `UPDATE`, `DROP`, `INSERT`.
- Safe queries execute automatically — dangerous ones require explicit approval.

---

### 🧍 4. Human-in-the-Loop Approval
- Requests user confirmation before executing any potentially harmful operation.
- Displays a polite, context-aware warning like:
  > ⚠️ "This action will delete records from the database. Would you like to proceed? (Yes / No)"
- Ensures **full transparency** and **database protection** at all times.

---

### 🧩 5. Autonomous SQL Execution Agent
- Executes the full SQL pipeline step by step:
  1. 📋 Lists all tables in the database
  2. 🧱 Retrieves table schemas
  3. 🧮 Constructs a valid SQL query
  4. ✅ Validates syntax before running
  5. ⚙️ Executes and returns the result
- After fetching results, it intelligently suggests visualization when appropriate.

---

### 📊 6. Data Visualization Agent
- Transforms SQL results into clean, **Matplotlib-powered charts**.
- Automatically selects the best chart type (Bar, Line, Pie, etc.) based on data.
- Saves charts with unique filenames per user and delivers natural-language insights:
  > "Here's a bar chart showing salary by department. You can see that Engineering earns the most."

---

### 💬 7. General Conversational Agent
- Handles non-database queries naturally.
- Equipped with a **live web search tool (Tavily)** for current events and real-world questions.
- Maintains awareness of its role inside the multi-agent system.

---

### 🔐 8. Authentication & User Isolation
- Secure **JWT-based login and registration**.
- Every user has their own **isolated database** and **chat history**.
- Sessions persist across browser refreshes via localStorage.

---

### 💾 9. Persistent Memory & Thread Management
- Uses **LangGraph's SQLite Checkpointer** for permanent conversation persistence.
- Maintains full context across sessions and multi-turn decisions.
- Users can **switch between past conversations** and **delete threads** from the sidebar.

---

### ⚡ 10. Real-Time Streaming
- Responses stream **token by token**, just like ChatGPT.
- Agent workflow steps are shown live as they execute:
  > `⚙️ checking user query → ⚙️ SQL Agent → ⚙️ visualization agent`

---

## 🚀 Highlights

- 🧠 **Self-Routing AI** — Intelligently picks the right agent for every query
- 🔒 **Safe by Design** — Human approval gate for all destructive operations
- 👁️ **Human Supervision** — User stays in full control at all times
- 📈 **Instant Visualization** — SQL results become charts automatically
- 🗣️ **Conversational Interface** — Chat naturally with your database
- 🔄 **Fully Autonomous Workflow** — Orchestrated by LangGraph
- 🌐 **Production Deployed** — Dockerized and live on Render with persistent storage

---

## 🧩 LangGraph Workflow

The diagram below shows how SQL Agent routes user queries between nodes:

<img src="Langgraph/SQL_Agent/agent_workflow.png" alt="LangGraph Workflow" width="700" />

---

## 🧱 Tech Stack

| Layer | Tools / Libraries |
|---|---|
| **Agent Framework** | LangGraph + LangChain |
| **LLM** | GPT-4.1 via GitHub Models API |
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | HTML / CSS / Vanilla JavaScript |
| **Database** | SQLite (via SQLAlchemy + aiosqlite) |
| **Auth** | JWT (python-jose + passlib + bcrypt) |
| **Visualization** | Matplotlib + Pandas |
| **Web Search** | Tavily Search API |
| **Memory** | LangGraph SQLite Checkpointer |
| **Deployment** | Docker + Render (persistent disk) |

---
## 🚀 Demo
https://github.com/user-attachments/assets/b8396347-db57-4913-bce6-bea23bfe929c

---


