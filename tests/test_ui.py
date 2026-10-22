"""Headless Streamlit integration tests using real widgets and reruns."""
from streamlit.testing.v1 import AppTest
from src.config import ROOT


def button(app, label):
    return next(b for b in app.button if b.label == label)


def assert_healthy(app):
    assert not app.exception, [e.message for e in app.exception]


def test_full_assessment_save_repeat_progress_clear(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH2PLACEMENT_DB", str(tmp_path / "history.sqlite3"))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    assert_healthy(app)
    button(app, "Start assessment  →").click().run()
    # Edit, go forward and backward, verify preserved draft.
    app.number_input[0].set_value(8.2)
    button(app, "Save section & continue →").click().run()
    button(app, "← Previous section").click().run()
    assert app.number_input[0].value == 8.2
    for i in range(5):
        button(app, "Review answers →" if i == 4 else "Save section & continue →").click().run()
        assert_healthy(app)
    button(app, "Calculate my readiness →").click().run()
    assert_healthy(app)
    first_score = app.session_state["result"]["score"]
    button(app, "Save assessment").click().run()
    assert app.success[0].value == "Saved to this workspace."
    button(app, "Update my answers").click().run()
    app.number_input[0].set_value(9.)
    for i in range(5):
        button(app, "Review answers →" if i == 4 else "Save section & continue →").click().run()
    button(app, "Calculate my readiness →").click().run()
    assert app.session_state["result"]["score"] > first_score
    button(app, "Save assessment").click().run()
    button(app, "View my progress").click().run()
    assert_healthy(app)
    assert app.metric[2].value == "2"
    assert len(app.get("download_button")) == 1
    app.checkbox(key="confirm_clear").check().run()
    button(app, "Permanently clear my history").click().run()
    assert_healthy(app)
    assert "starting line" in app.info[0].value


def test_review_validation_no_crash(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH2PLACEMENT_DB", str(tmp_path / "history.sqlite3"))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    app.session_state["step"] = 5
    app.session_state["draft"]["demos"] = 5
    button(app, "Start assessment  →").click().run()
    assert_healthy(app)
    assert "cannot exceed" in app.error[0].value
    assert button(app, "Calculate my readiness →").disabled


def page_test(function):
    return AppTest.from_string(f"import streamlit as st\nfrom src import ui\nst.set_page_config(layout='wide')\nui.initialize()\nui.styles()\nui.{function}()", default_timeout=15).run()


def test_model_insights_and_inference():
    app = page_test("model_insights")
    assert_healthy(app)
    assert len(app.metric) == 7
    button(app, "Run simulated inference").click().run()
    assert_healthy(app)
    assert "Simulated exercise class" in app.info[-1].value


def test_about_and_empty_results_and_progress(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH2PLACEMENT_DB", str(tmp_path / "history.sqlite3"))
    for page in ["about", "results", "progress"]:
        assert_healthy(page_test(page))


def test_database_failure_keeps_home_usable(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH2PLACEMENT_DB", str(tmp_path))
    app = page_test("home")
    assert_healthy(app)
    assert "Cannot access" in app.warning[0].value


def test_section_validation_preserves_values(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH2PLACEMENT_DB", str(tmp_path / "history.sqlite3"))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=15).run()
    button(app, "Start assessment  →").click().run()
    button(app, "Save section & continue →").click().run()
    next(n for n in app.number_input if "languages" in n.label).set_value(0)
    button(app, "Save section & continue →").click().run()
    assert_healthy(app)
    assert app.session_state["step"] == 1
    assert "no programming languages" in app.error[0].value
    assert app.session_state["draft"]["languages"] == 0
