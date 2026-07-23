# Example: Using ContextGraph on a small backend-like project
# This demonstrates improved query + semantic search

from contextgraph import CodeContextGraph

import tempfile
 import os
 from pathlib import Path

# Create a tiny demo project in temp dir
def create_demo_project():
    tmp = tempfile.mkdtemp(prefix="cg_demo_")
    (Path(tmp) / "auth.py").write_text('''
def login_user(username, password):
    """Authenticate user and return token."""
    if not username or not password:
        raise ValueError("Missing credentials")
    # TODO: real implementation
    return {"token": "fake.jwt.token", "user_id": 42}

def verify_token(token):
    """Check if token is valid."""
    return token.startswith("fake")
''')

    (Path(tmp) / "db.py").write_text('''
import sqlite3

def get_db_connection():
    """Return database connection with pooling hints."""
    conn = sqlite3.connect(":memory:")
    return conn

def fetch_user(user_id):
    conn = get_db_connection()
    # placeholder
    return {"id": user_id, "name": "demo"}
''')

    (Path(tmp) / "main.py").write_text('''
from auth import login_user, verify_token

if __name__ == "__main__":
    token = login_user("admin", "secret")
    print(verify_token(token["token"]))
''')
    return tmp

if __name__ == "__main__":
    project_path = create_demo_project()
    print(f"Demo project created at: {project_path}")

    cg = CodeContextGraph()
    cg.load_project(project_path)
    cg.build_graph()

    print("\n=== Basic query ===")
    res1 = cg.query_context("login or authentication", max_tokens=800)
    print(res1["context"][:800])

    print("\n=== With semantic (if available) ===")
    if cg.enable_semantic_search():
        res2 = cg.query_context("user login flow", max_tokens=800, use_semantic=True)
        print(res2["context"][:800])
