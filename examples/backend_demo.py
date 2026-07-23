from __future__ import annotations

import tempfile
from pathlib import Path

from contextgraph import CodeContextGraph


def create_demo_project() -> Path:
    """Create a disposable backend-style Python project."""
    project = Path(tempfile.mkdtemp(prefix="contextgraph_demo_"))
    (project / "auth.py").write_text(
        '''
def login_user(username, password):
    """Authenticate a user and return a token."""
    if not username or not password:
        raise ValueError("Missing credentials")
    return {"token": "demo.jwt.token", "user_id": 42}


def verify_token(token):
    """Return whether a demo token is valid."""
    return token.startswith("demo")
'''.strip(),
        encoding="utf-8",
    )
    (project / "db.py").write_text(
        '''
import sqlite3


def get_db_connection():
    return sqlite3.connect(":memory:")


def fetch_user(user_id):
    connection = get_db_connection()
    connection.close()
    return {"id": user_id, "name": "demo"}
'''.strip(),
        encoding="utf-8",
    )
    return project


def main() -> None:
    project = create_demo_project()
    print(f"Demo project: {project}")

    graph = CodeContextGraph()
    graph.load_project(project)
    graph.build_graph()

    result = graph.query_context("login authentication", max_tokens=300)
    print("\n=== Retrieved context ===")
    print(result["context"])


if __name__ == "__main__":
    main()
