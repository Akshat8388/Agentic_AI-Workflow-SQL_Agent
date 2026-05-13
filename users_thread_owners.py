import sqlite3

conn = sqlite3.connect("/workspaces/Gen_AI/Langgraph/SQL_Agent/database/agent_memory.db")

conn.execute("""
    CREATE TABLE IF NOT EXISTS thread_owners (
        thread_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
""")

conn.commit()
conn.close()

print("thread_owners table created!")