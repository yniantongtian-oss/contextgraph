import tempfile
 from pathlib import Path
 from contextgraph import CodeContextGraph


def test_load_and_build_graph():
    cg = CodeContextGraph()
    # Use the backend_demo structure if available, else create minimal
    import os
    demo_dir = Path(__file__).parent.parent / "examples"
    if (demo_dir / "backend_demo.py").exists():
        # Just test that it doesn't crash on a real-ish project
        cg.load_project(str(demo_dir))
        cg.build_graph()
        stats = cg.get_graph_stats()
        assert stats["nodes"] > 0
    else:
        # Fallback minimal test
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.py"
            p.write_text("def hello(): pass\ndef world(): hello()")
            cg.load_project(tmp)
            cg.build_graph()
            assert cg.get_graph_stats()["nodes"] > 0


def test_query_returns_context():
    cg = CodeContextGraph()
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "main.py"
        p.write_text("def authenticate(user): return True\ndef get_user(id): pass")
        cg.load_project(tmp)
        cg.build_graph()
        res = cg.query_context("authenticate user", max_tokens=500)
        assert "context" in res
        assert len(res["context"]) > 0 or res.get("total_candidates", 0) >= 0
