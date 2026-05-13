import sqlite3

# Connect to local DB file
conn = sqlite3.connect("Langgraph/SQL_Agent/backend/SampleDatabase/company_database.db")
cursor = conn.cursor()

# --- Create tables ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    location TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    age INTEGER,
    department_id INTEGER,
    salary REAL,
    FOREIGN KEY (department_id) REFERENCES departments (id)
)
""")

# --- Expanded sample data ---
departments_data = [
    (1, 'Sales', 'New York'),
    (2, 'Engineering', 'San Francisco'),
    (3, 'HR', 'Chicago'),
    (4, 'Marketing', 'Los Angeles'),
    (5, 'Finance', 'Boston'),
    (6, 'Customer Support', 'Dallas'),
    (7, 'IT', 'Seattle'),
    (8, 'Operations', 'Houston'),
    (9, 'Legal', 'Washington D.C.'),
    (10, 'R&D', 'Austin'),
]

employees_data = [
    (1, 'Alice Johnson', 30, 1, 55000),
    (2, 'Bob Smith', 45, 2, 90000),
    (3, 'Carol Davis', 25, 3, 40000),
    (4, 'David Wilson', 38, 1, 60000),
    (5, 'Emma Brown', 29, 2, 80000),
    (6, 'Frank Martin', 41, 3, 45000),
    (7, 'Grace Lee', 34, 4, 65000),
    (8, 'Henry Adams', 28, 5, 70000),
    (9, 'Ivy Clark', 32, 6, 50000),
    (10, 'Jack Turner', 27, 7, 48000),
    (11, 'Karen Scott', 36, 8, 62000),
    (12, 'Leo Walker', 39, 9, 75000),
    (13, 'Mia Hall', 26, 10, 55000),
    (14, 'Nathan Young', 31, 1, 58000),
    (15, 'Olivia King', 33, 2, 81000),
    (16, 'Peter Wright', 42, 3, 46000),
    (17, 'Quinn Baker', 29, 4, 67000),
    (18, 'Rachel Hill', 35, 5, 72000),
    (19, 'Samuel Green', 37, 6, 52000),
    (20, 'Tina Moore', 30, 7, 49000),
    (21, 'Umar Patel', 28, 8, 61000),
    (22, 'Victoria Reed', 40, 9, 78000),
    (23, 'William Cox', 27, 10, 57000),
    (24, 'Xavier Bell', 31, 1, 59000),
    (25, 'Yara Price', 34, 2, 82000),
    (26, 'Zane Diaz', 38, 3, 47000),
    (27, 'Amy Simmons', 29, 4, 68000),
    (28, 'Brian Foster', 33, 5, 73000),
    (29, 'Chloe Ross', 36, 6, 53000),
    (30, 'Derek Hughes', 41, 7, 50000),
]

# --- Insert data ---
cursor.executemany("INSERT OR REPLACE INTO departments VALUES (?, ?, ?)", departments_data)
cursor.executemany("INSERT OR REPLACE INTO employees VALUES (?, ?, ?, ?, ?)", employees_data)

conn.commit()
conn.close()

print("✅ company_database.db created successfully with expanded data!")
