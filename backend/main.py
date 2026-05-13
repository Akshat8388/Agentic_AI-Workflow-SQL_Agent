from contextlib import asynccontextmanager
from fastapi import FastAPI,HTTPException,Depends
from fastapi.middleware.cors import CORSMiddleware
from auth import hash_password, verify_password, create_token, get_user_by_username, create_user, get_current_user,save_thread_owner
from pydantic import BaseModel
from typing import Optional
from langchain_core.messages import HumanMessage,AIMessage
import json
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import os
import re
import shutil
from sql_agent import graph

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

frontend_dir = os.path.join(BASE_DIR, '..', 'frontend')
scripts_dir = os.path.join(frontend_dir, 'scripts')
styles_dir = os.path.join(frontend_dir, 'styles')

# Use env vars if set (Docker/production), fall back to local paths for dev
MEMORY_DB_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "../database/agent_memory.db"))
SAMPLE_DB_PATH = os.path.join(BASE_DIR, "SampleDatabase/company_database.db")
USER_DATA_DIR = os.getenv("USER_DATA_DIR", os.path.join(BASE_DIR, "user_data"))
plots_dir = os.getenv("PLOTS_DIR", os.path.join(BASE_DIR, "plots"))

# lifespan initializes the agent
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure persistent directories exist
    os.makedirs(os.path.dirname(os.path.abspath(MEMORY_DB_PATH)), exist_ok=True)
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)

    # Auto-initialize DB tables (users + thread_owners)
    import sqlite3 as _sqlite3
    _conn = _sqlite3.connect(MEMORY_DB_PATH)
    _conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    _conn.execute("""CREATE TABLE IF NOT EXISTS thread_owners (
        thread_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")
    _conn.commit()
    _conn.close()

    async with AsyncSqliteSaver.from_conn_string(MEMORY_DB_PATH) as saver:
        app.state.agent = graph.compile(
            checkpointer=saver,
            interrupt_after=["human_approval"]
        )
        yield

app = FastAPI(title="SQLAgent API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(plots_dir, exist_ok=True)
app.mount("/scripts", StaticFiles(directory=scripts_dir), name="scripts")
app.mount("/styles", StaticFiles(directory=styles_dir), name="styles")
app.mount("/plots", StaticFiles(directory=plots_dir), name="plots")


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ConnectDBRequest(BaseModel):
    db_uri: str

class QueryRequest(BaseModel):
    user_message: Optional[str] = None
    db_path: Optional[str] = None
    status: Optional[str] = None
    thread_id: str

def get_user_sample_db(user_id: int) -> str:
    user_db_dir = os.path.join(USER_DATA_DIR, str(user_id))
    user_db_path = os.path.join(user_db_dir, "company_database.db")
    os.makedirs(user_db_dir, exist_ok=True)
    
    # Copy fresh sample DB only if user doesn't have one yet
    if not os.path.exists(user_db_path):
        shutil.copy(SAMPLE_DB_PATH, user_db_path)
    
    return user_db_path

@app.get("/sample-db")
async def get_sample_db(user = Depends(get_current_user)):
    user_id = user["user_id"]
    db_path = get_user_sample_db(user_id)
    return {"db_path": f"sqlite:///{db_path}"}

@app.post("/connect-db")
async def connect_db(request: ConnectDBRequest, user = Depends(get_current_user)):
    from langchain_community.utilities import SQLDatabase
    try:
        db = SQLDatabase.from_uri(request.db_uri)
        db.run("SELECT 1")
        return {"success": True, "db_path": request.db_uri}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")

@app.post("/register")
def register(request: RegisterRequest):
    hashed = hash_password(request.password)
    create_user(request.username, request.email, hashed)
    return {"message": f"User '{request.username}' registered successfully"}

@app.post("/login")
def login(request: LoginRequest):
    user = get_user_by_username(request.username)
    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_token(user["id"], user["username"])
    return {"access_token": token, "username": user["username"]}

@app.get("/threads")
async def get_all_threads(user = Depends(get_current_user)):
    user_id = user["user_id"]
    agent = app.state.agent
    threads = []

    try:
        conn = agent.checkpointer.conn
        async with conn.execute(
            """SELECT c.thread_id 
               FROM checkpoints c
               INNER JOIN thread_owners t ON c.thread_id = t.thread_id
               WHERE t.user_id = ?
               GROUP BY c.thread_id 
               ORDER BY MAX(c.checkpoint_id) DESC""",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()

        for row in rows:
            tid = row[0]
            config = {"configurable": {"thread_id": tid}}
            try:
                state = await agent.aget_state(config)
                msgs = state.values.get("messages", []) if state and state.values else []
                title = next(
                    (m.content[:40] + "…" if len(m.content) > 40 else m.content
                     for m in msgs if m.type in ["human", "user"]),
                    "Untitled"
                )
                threads.append({"id": tid, "title": title})
            except Exception:
                continue

    except Exception as e:
        return {"threads": [], "error": str(e)}

    return {"threads": threads}

@app.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str, user = Depends(get_current_user)):
    """Deletes all checkpoints for a given thread from the SQLite DB."""
    user_id = user["user_id"]
    agent = app.state.agent
    try:
        conn = agent.checkpointer.conn

        # Verify the thread belongs to this user before deleting
        async with conn.execute(
            "SELECT 1 FROM thread_owners WHERE thread_id = ? AND user_id = ?",
            (thread_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=403, detail="Not authorized to delete this thread")

        await conn.execute(
            "DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,)
        )
        await conn.execute(
            "DELETE FROM writes WHERE thread_id = ?", (thread_id,)
        )
        await conn.execute(
            "DELETE FROM thread_owners WHERE thread_id = ?", (thread_id,)
        )
        await conn.commit()
        return {"deleted": True, "thread_id": thread_id}
    except HTTPException:
        raise
    except Exception as e:
        return {"deleted": False, "error": str(e)}
    
@app.get("/chat_history/{thread_id}")
async def get_chat_history(thread_id: str,user = Depends(get_current_user)):
    user_id = user["user_id"]
    agent = app.state.agent
    config = {"configurable": {"thread_id": thread_id}}
    state = await agent.aget_state(config)

    if not state or not state.values:
        return {"messages": []}

    history = []
    for msg in state.values.get("messages", []):
        if msg.type in ["human", "user"]:
            history.append({"sender": "user", "text": str(msg.content)})

        elif msg.type in ["ai", "assistant"] and msg.content:
            content = str(msg.content)

            # Detect embedded image path tag
            img_match = re.search(r'\[IMG\](.*?)\[/IMG\]', content)
            if img_match:
                img_path = img_match.group(1)
                # Clean text — remove the [IMG] tag from visible text
                clean_text = re.sub(r'\[IMG\].*?\[/IMG\]', '', content).strip()
                if clean_text:
                    history.append({"sender": "ai", "text": clean_text})
                # Send image as separate entry
                history.append({"sender": "ai", "type": "image", "img_url": img_path})
            else:
                history.append({"sender": "ai", "text": content})

    return {"messages": history}

@app.post("/chat")
async def chat_with_agent(request: QueryRequest,user = Depends(get_current_user)):
    user_id = user["user_id"]

    conn = app.state.agent.checkpointer.conn
    await save_thread_owner(request.thread_id, user_id, conn)
    async def stream_events():
        agent = app.state.agent
        config = {"configurable": {"thread_id": request.thread_id,"run_name": f"chat-{request.thread_id[:8]}"}}
        try:
            initial_state = {
                "messages": [HumanMessage(content=request.user_message)],
                "db_path": request.db_path,
                "user_id": user_id
            }
            seen_nodes = set()
            token_buffer = ""  # buffer to detect and strip [IMG] tag from stream

            async for event in agent.astream_events(initial_state, config=config, version="v1"):
                node_name = event["metadata"].get("langgraph_node")
                evt = event["event"]

                if evt == "on_chain_start" and node_name in [
                    "checking_user_query", "checking_database_connection",
                    "human_approval", "query_safety_analysis",
                    "SQL_Agent", "general_LLM_agent", "visualization_agent"
                ]:
                    if node_name not in seen_nodes:
                        seen_nodes.add(node_name)
                        yield json.dumps({"node_executed": node_name}) + "\n"

                elif evt == "on_chat_model_stream" and node_name in [
                    "agent", "general_LLM_agent", "visualization_agent"
                ]:
                    content = event["data"]["chunk"].content
                    if content:
                        token_buffer += content
                        # Strip [IMG]...[/IMG] from streamed output
                        clean = re.sub(r'\[IMG\].*?\[/IMG\]', '', token_buffer)
                        if clean != token_buffer:
                            token_buffer = ""
                        yield json.dumps({"token": content}) + "\n"

                elif evt == "on_chain_end" and node_name == "visualization_agent":
                    output = event["data"].get("output", {})
                    img_path = output.get("img_path") if isinstance(output, dict) else None
                    if img_path:
                        yield json.dumps({"img_url": img_path}) + "\n"

                elif evt == "on_chain_stream" and node_name == "checking_database_connection":
                    data = event["data"]["chunk"]
                    if "messages" in data:
                        for msg in data["messages"]:
                            yield json.dumps({"token": msg.content}) + "\n"

                elif evt == "on_chain_stream" and node_name == "human_approval":
                    data = event["data"]["chunk"]
                    warning = data.get("warning_msg")
                    if warning:
                        warning_content = (
                            warning[0].content if isinstance(warning, list)
                            else getattr(warning, "content", str(warning))
                        )
                        yield json.dumps({"warning": warning_content}) + "\n"

        except Exception as e:
            yield json.dumps({"error": f"An error occurred: {str(e)}"}) + "\n"
    return StreamingResponse(stream_events(), media_type="application/x-ndjson")

@app.post("/resume")
async def resume_agent(request: QueryRequest,user = Depends(get_current_user)):
    user_id = user["user_id"]
    async def stream_remaining_events():

        agent = app.state.agent
        config = {"configurable": {"thread_id": request.thread_id,"run_name": f"chat-{request.thread_id[:8]}"}}
        try:
            if request.status == "no":
                yield json.dumps({"agent": "❌ Action cancelled by user."}) + "\n"
                await agent.aupdate_state(config = config,values = {"messages":AIMessage(content = "❌ Action cancelled by user.")})
                await agent.aupdate_state(config=config, values={"status": None})
                return

            await agent.aupdate_state(config=config, values={"status": request.status})

            async for event in agent.astream_events(None, config=config, version="v1"):
                if event["event"] == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield json.dumps({"agent": content}) + "\n"

            # Reset status after done
            await agent.aupdate_state(config=config, values={"status": None})

        except Exception as e:
            yield json.dumps({"error": f"An error occurred during resume: {str(e)}"}) + "\n"

        yield json.dumps({"done": True}) + "\n"

    return StreamingResponse(stream_remaining_events(), media_type="application/x-ndjson")

@app.get("/", response_class=HTMLResponse)
def serve_root():
    return FileResponse(os.path.join(BASE_DIR, "../frontend/index.html"))