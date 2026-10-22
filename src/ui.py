"""Streamlit presentation. Business logic lives in the other src modules."""
import html
import secrets
import uuid
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from src.config import CATEGORY_WEIGHTS, CATEGORY_FIELDS, FIELDS, SECTION_HELP, SCORING_VERSION
from src.database import HistoryStore, HistoryError, export_csv, owner_id
from src.readiness_scoring import assess, validate_inputs, ValidationError
from src.recommendations import recommend, seven_day_plan
from src.predict import load_model, predict_simulated, ModelError

GREEN = "#245C48"
CATEGORIES = list(CATEGORY_WEIGHTS)


def initialize():
    defaults = {"workspace_key": secrets.token_hex(32), "draft": {k: v[3] for k, v in FIELDS.items()}, "step": 0}
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def styles():
    st.markdown('''<style>
    :root { --forest:#245C48; --muted:#636B64; }
    html, body, [class*="css"] {font-family: "Inter", "Segoe UI", sans-serif;}
    .block-container {max-width:1220px;padding:2.3rem 3rem 3.5rem;}
    [data-testid="stSidebar"] {border-right:1px solid #E0E3DA;}
    [data-testid="stSidebar"] > div:first-child {padding-top:1.1rem;}
    [data-testid="stHeader"] {background:transparent;}
    h1 {font-size:2.35rem!important;letter-spacing:-.075rem;line-height:1.18!important;font-weight:650!important;}
    h2 {font-size:1.45rem!important;letter-spacing:-.035rem;font-weight:620!important;}
    h3 {font-size:1.08rem!important;font-weight:620!important;}
    p {line-height:1.65;}
    .eyebrow {font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;color:#636B64;font-weight:650;margin:0 0 .8rem;}
    .lede {font-size:1.05rem;color:#636B64;max-width:680px;line-height:1.7;margin:.7rem 0 1.5rem;}
    .brand {display:flex;gap:.7rem;align-items:center;padding:0 .6rem 1.7rem;font-weight:650;font-size:1.08rem;letter-spacing:-.025rem;}
    .brand-mark {background:#245C48;color:#fff;display:flex;align-items:center;justify-content:center;width:35px;height:39px;border-radius:5px;font-size:1.4rem;}
    .brand small {display:block;font-size:.57rem;letter-spacing:.14em;color:#636B64;margin-top:.2rem;}
    .sidebar-note {border-top:1px solid #D9DED4;padding:1.2rem .5rem 0;margin-top:1.5rem;font-size:.78rem;line-height:1.8;color:#636B64;}
    .sidebar-note strong {font-weight:500;color:#245C48;}
    .hero-note {border-left:3px solid #245C48;padding:.15rem 0 .15rem 1.1rem;color:#636B64;font-size:.88rem;margin:1.7rem 0 1.5rem;}
    .section-row {display:flex;gap:1rem;align-items:baseline;border-bottom:1px solid #E0E3DA;padding:1rem 0;}
    .row-num {font-size:.78rem;color:#636B64;font-variant-numeric:tabular-nums;min-width:1.5rem;}
    .row-body {flex:1;} .row-body strong {font-size:.94rem;font-weight:600;} .row-body p {font-size:.82rem;color:#636B64;margin:.25rem 0 0;line-height:1.5;}
    .weight {font-size:.8rem;color:#245C48;white-space:nowrap;}
    .side-panel {background:#EAF0E7;border:1px solid #D9E2D5;padding:1.5rem;border-radius:5px;}
    .side-panel h3 {margin-top:0;padding-top:0;} .side-panel p {font-size:.9rem;color:#4F5D50;}
    .side-panel .line {border-top:1px solid #CFDACB;margin:1rem 0;}
    .big-score {font-size:4.8rem;line-height:1.1;font-weight:600;letter-spacing:-.25rem;color:#245C48;margin:.8rem 0 .4rem;}
    .big-score small {font-size:1.3rem;letter-spacing:0;color:#636B64;}
    .band {display:inline-block;background:#E5EDDF;border:1px solid #D2DDC9;color:#245C48;padding:.25rem .65rem;font-size:.83rem;border-radius:3px;}
    .steps {display:flex;gap:.6rem;margin:1rem 0 1.5rem;}
    .step {flex:1;border-top:3px solid #DEE2D8;padding-top:.5rem;font-size:.75rem;color:#636B64;}
    .step.active {border-color:#245C48;color:#245C48;font-weight:650;}
    .rec {border-top:1px solid #E0E3DA;padding:1rem 0 .7rem;}
    .rec .tag {font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;color:#636B64;}
    .rec h3 {margin:.25rem 0!important;padding:0!important;}
    .rec p {font-size:.89rem;margin:.35rem 0;}
    .rec .reason {color:#636B64;font-size:.8rem;}
    div[data-testid="stMetric"] {border-bottom:1px solid #DFE4D8;padding-bottom:1rem;}
    [data-testid="stMetricValue"] {font-size:2rem;}
    div.stButton > button, div.stFormSubmitButton > button {border-radius:4px;min-height:2.7rem;font-weight:550;}
    [data-testid="stAlert"] {border-radius:4px;}
    hr {margin:1.6rem 0!important;border-color:#E0E3DA;}
    @media(max-width:768px){.block-container{padding:5rem 1rem 2rem!important;}h1{font-size:1.9rem!important;}.step{font-size:.62rem;}.steps{gap:.3rem;}.big-score{font-size:4rem;}}
    </style>''', unsafe_allow_html=True)


def go_page(name):
    st.switch_page(st.session_state["pages"][name])


def header(kicker, title, description):
    st.markdown(f'<div class="eyebrow">{kicker}</div>', unsafe_allow_html=True)
    st.title(title)
    if description:
        st.markdown(f'<div class="lede">{description}</div>', unsafe_allow_html=True)


def workspace_controls():
    with st.expander("Local history & privacy", icon=":material/lock:"):
        st.caption("History lives on the server running this app, not in your browser. It is separated by a random workspace key—not an account or password.")
        st.caption("Copy your recovery key before closing this session. A new session starts a new workspace. Never share the key; anyone with it can open your history. Server administrators can access the database.")
        if st.checkbox("Show my recovery key", key="show_recovery"):
            st.code(st.session_state["workspace_key"], language=None, wrap_lines=True)
        with st.form("restore_workspace", clear_on_submit=True):
            key = st.text_input("Open an existing workspace", type="password", placeholder="64-character recovery key")
            restore = st.form_submit_button("Open workspace")
        if restore:
            try:
                owner_id(key.strip())
                st.session_state["workspace_key"] = key.strip()
                for k in ("result", "assessment_id", "saved_id"):
                    st.session_state.pop(k, None)
                st.session_state["draft"] = {k: v[3] for k, v in FIELDS.items()}
                st.session_state["step"] = 0
                st.rerun()
            except HistoryError as exc:
                st.error(str(exc))
        if st.button("Create a fresh workspace", width="stretch"):
            st.session_state["workspace_key"] = secrets.token_hex(32)
            for k in ("result", "assessment_id", "saved_id"):
                st.session_state.pop(k, None)
            st.session_state["draft"] = {k: v[3] for k, v in FIELDS.items()}
            st.session_state["step"] = 0
            st.rerun()


def history():
    try:
        return HistoryStore().list(st.session_state["workspace_key"])
    except HistoryError as exc:
        st.warning(str(exc))
        return []


def chart_theme(fig, height=320):
    fig.update_layout(height=height, margin=dict(l=0, r=10, t=15, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Arial, sans-serif", color="#4E574F", size=12))
    fig.update_xaxes(gridcolor="#E3E6DD", zeroline=False)
    fig.update_yaxes(gridcolor="#E3E6DD", zeroline=False)
    return fig


def category_chart(categories):
    df = pd.DataFrame({"Category": list(categories), "Score": list(categories.values())})
    fig = px.bar(df, x="Score", y="Category", orientation="h", text="Score", color_discrete_sequence=[GREEN])
    fig.update_traces(texttemplate="%{x:.0f}", textposition="outside", cliponaxis=False, width=.47, hovertemplate="%{y}: %{x:.2f}/100<extra></extra>")
    fig.update_xaxes(range=[0, 108], title=None, tickvals=[0, 25, 50, 75, 100])
    fig.update_yaxes(autorange="reversed", title=None)
    return chart_theme(fig, 290)


def home():
    header("Your preparation, in perspective", "A clearer path to placement readiness.",
           "Understand where you stand. Find what to work on next.<br>Turn an honest self-assessment into a practical week of preparation.")
    left, right = st.columns([1.65, 1], gap="large")
    with left:
        if st.button("Start assessment  →", type="primary", key="start_home"):
            go_page("assess")
        st.caption("Five sections · about 5–8 minutes · no account needed")
        st.markdown('<div class="hero-note">Preparation, not a prediction of your future.<br>This score reflects our selected criteria—not your probability of getting hired.</div>', unsafe_allow_html=True)
        st.subheader("The five parts of your preparation")
        descriptions = ["CGPA, consistency and core-subject understanding.", "Programming fundamentals, DSA and deliberate practice.",
                        "Working demos, documentation and depth of understanding.", "Practice-test results and explaining ideas clearly.", "A verifiable resume, project walkthroughs and interview practice."]
        for i, (category, weight) in enumerate(CATEGORY_WEIGHTS.items()):
            st.markdown(f'<div class="section-row"><span class="row-num">0{i+1}</span><div class="row-body"><strong>{category}</strong><p>{descriptions[i]}</p></div><span class="weight">{weight:.0%}</span></div>', unsafe_allow_html=True)
    with right:
        records = history()
        if records:
            latest = records[-1]
            st.markdown(f'<div class="side-panel"><div class="eyebrow">Your latest saved assessment</div><div class="big-score">{latest["score"]:.0f}<small> / 100</small></div><span class="band">{latest["band"]}</span><div class="line"></div><p>{len(records)} saved assessment(s) in this workspace.<br>Last assessed {latest["created_at"][:10]} (UTC).</p></div>', unsafe_allow_html=True)
            if st.button("See my progress", width="stretch"):
                go_page("progress")
        else:
            st.markdown('''<div class="side-panel"><div class="eyebrow">A starting point, not a finish line</div><h3>Small steps. Better direction.</h3><p>Your first assessment gives you a baseline to build on. There is no comparison with other students.</p><div class="line"></div><h3>Leave with a practical plan</h3><p>A score you can explain.<br>Five category breakdowns.<br>Your priorities, in order.<br>A seven-day starter plan.</p></div>''', unsafe_allow_html=True)
            st.caption("No assessments saved yet. Your progress will appear here after you choose to save a result.")
        st.markdown("#### Built to be transparent")
        st.write("The readiness score uses documented rules. The separate ML learning lab uses synthetic data. Neither guarantees a job offer.")
        if st.button("Explore the methodology", key="home_method"):
            go_page("about")


def render_field(key):
    label, low, high, _, optional, cap = FIELDS[key]
    value = st.session_state["draft"][key]
    widget_key = f"assessment_{key}_{owner_id(st.session_state['workspace_key'])}"
    if key == "internship":
        choice = st.selectbox(label, ["No experience yet", "Completed an internship"], index=int(value), key=widget_key, help="Only 5% of the projects category. Not having an internship is not a barrier to starting.")
        return int(choice == "Completed an internship")
    if low == 1 and high == 5:
        return st.select_slider(label, options=[1, 2, 3, 4, 5], value=int(value), key=widget_key,
                                format_func=lambda n: {1:"1 · Beginner",2:"2 · Basic",3:"3 · Intermediate",4:"4 · Strong",5:"5 · Advanced"}[n],
                                help="Self-rating: 1 needs guided examples; 2 handles basics with help; 3 works independently on familiar tasks; 4 handles unfamiliar tasks; 5 can teach and justify trade-offs.")
    help_text = "Leave blank if you have not taken this test. Its weight is redistributed within this category." if optional else "Use your current, honest preparation—not a target."
    if cap:
        help_text += f" Contribution is capped at {cap}; higher counts do not add points."
    if isinstance(low, float):
        return st.number_input(label, min_value=low, max_value=high, value=None if value is None else float(value), step=.1 if key == "cgpa" else 1., key=widget_key, help=help_text, placeholder="Not taken / unknown" if optional else None)
    return st.number_input(label, min_value=low, max_value=high, value=int(value), step=1, key=widget_key, help=help_text)


def assessment():
    header("An honest snapshot", "Assess my readiness", "Think about what you can demonstrate today. You can go back at any point; your submitted section answers stay in this session.")
    step = st.session_state["step"]
    labels = ["Academics", "Programming", "Projects", "Aptitude", "Interview"]
    st.markdown('<div class="steps">' + ''.join(f'<div class="step {"active" if i == step or step == 5 else ""}">{i+1:02d} · {label}</div>' for i, label in enumerate(labels)) + '</div>', unsafe_allow_html=True)
    if step < 5:
        category = CATEGORIES[step]
        st.caption(f"SECTION {step+1} OF 5")
        st.subheader(category)
        st.write(SECTION_HELP[category])
        if any(FIELDS[k][1:3] == (1, 5) for k in CATEGORY_FIELDS[category]):
            st.caption("Self-rating scale: 1 Beginner · 2 Basic · 3 Intermediate · 4 Strong · 5 Advanced. These are not objective test results.")
        with st.form(f"section_{step}"):
            cols = st.columns(2, gap="large")
            values = {}
            for i, key in enumerate(CATEGORY_FIELDS[category]):
                with cols[i % 2]:
                    values[key] = render_field(key)
            st.divider()
            left, right = st.columns(2)
            with left:
                back = st.form_submit_button("← Previous section", disabled=step == 0)
            with right:
                next_step = st.form_submit_button("Review answers →" if step == 4 else "Save section & continue →", type="primary", width="stretch")
        if next_step or back:
            st.session_state["draft"].update(values)
            try:
                if next_step:
                    validate_inputs(st.session_state["draft"], fields=CATEGORY_FIELDS[category])
                st.session_state["step"] = step + (1 if next_step else -1)
                st.rerun()
            except ValidationError as exc:
                st.error(str(exc))
        st.caption("Section answers are temporary until you calculate and explicitly save your result. Use the section buttons before navigating away.")
    else:
        st.subheader("A quick review before your results")
        st.write("Check your answers below. Missing optional scores are excluded; other criteria in that category receive proportionally more weight.")
        draft = st.session_state["draft"]
        for category, fields in CATEGORY_FIELDS.items():
            with st.expander(category):
                st.dataframe(pd.DataFrame({"Input": [FIELDS[k][0] for k in fields], "Your answer": [str(draft[k]) if draft[k] is not None else "Not provided" for k in fields]}), hide_index=True, width="stretch")
        try:
            result = assess(draft)
            valid = True
        except ValidationError as exc:
            st.error(str(exc))
            valid = False
        left, right = st.columns(2)
        with left:
            if st.button("← Edit my answers"):
                st.session_state["step"] = 0
                st.rerun()
        with right:
            if st.button("Calculate my readiness →", type="primary", disabled=not valid, width="stretch"):
                st.session_state["result"] = result
                st.session_state["assessment_id"] = str(uuid.uuid4())
                st.session_state.pop("saved_id", None)
                go_page("results")
        st.caption("This calculates a transparent preparation score, not an employment probability. Nothing is saved to history until you choose Save assessment.")


def results():
    header("Your next steps start here", "A snapshot of your preparation", "Use this as a guide for practice, not a verdict. Progress comes from the evidence you build over time.")
    if "result" not in st.session_state:
        st.info("Complete an assessment to see your score, priorities and seven-day plan.")
        if st.button("Start my assessment", type="primary"):
            go_page("assess")
        return
    result = st.session_state["result"]
    left, right = st.columns([1, 1.9], gap="large")
    with left:
        st.markdown(f'<div class="eyebrow">Readiness score · rules-based</div><div class="big-score">{result["score"]:.0f}<small> / 100</small></div><span class="band">{result["band"]}</span>', unsafe_allow_html=True)
        st.caption(f"Exact score: {result['score']:.2f} · Scoring version {result['scoring_version']}")
        if st.session_state.get("saved_id"):
            st.success("Saved to this workspace.")
        elif st.button("Save assessment", type="primary", width="stretch"):
            try:
                st.session_state["saved_id"] = HistoryStore().save(st.session_state["workspace_key"], result, recommend(result["inputs"]), st.session_state["assessment_id"])
                st.rerun()
            except HistoryError as exc:
                st.error(str(exc))
        if st.button("View my progress", width="stretch"):
            go_page("progress")
        st.caption("Save your workspace recovery key in the sidebar to reopen history in a later session.")
    with right:
        st.subheader("Your preparation by category")
        st.plotly_chart(category_chart(result["categories"]), width="stretch", theme=None, config={"displayModeBar": False})
    if result["missing_optional"]:
        st.info("Not provided: " + ", ".join(FIELDS[k][0] for k in result["missing_optional"]) + ". Remaining weights are rescaled within those categories. Scores with different missing inputs are not directly comparable.")
    categories = sorted(result["categories"].items(), key=lambda pair: pair[1], reverse=True)
    a, b = st.columns(2, gap="large")
    with a:
        st.subheader("What to build on")
        for category, score in categories[:2]:
            st.write(f"**{category} · {score:.0f}/100**")
        st.caption("Your relatively strongest categories—not proof of mastery. Validate self-ratings with practice and feedback.")
    with b:
        st.subheader("Where to focus next")
        for category, score in reversed(categories[-2:]):
            st.write(f"**{category} · {score:.0f}/100**")
        st.caption("Your lower-scoring categories offer a starting point. Start small rather than trying to improve everything at once.")
    st.divider()
    tabs = st.tabs(["Priority actions", "Your seven-day plan", "How this score works"])
    with tabs[0]:
        actions = recommend(result["inputs"])
        st.caption("Ordered by the score of the affected category. Begin with the first two or three; the rest can wait.")
        for i, action in enumerate(actions):
            st.markdown(f'<div class="rec"><span class="tag">{i+1:02d} · {action["priority"]}</span><h3>{html.escape(action["title"])}</h3><p class="reason">{html.escape(action["reason"])}</p><p>{html.escape(action["task"])}</p><p><strong>Done when:</strong> {html.escape(action["criterion"])}</p></div>', unsafe_allow_html=True)
    with tabs[1]:
        plan = pd.DataFrame(seven_day_plan(result["inputs"]))
        st.caption("A manageable starter week: 30–45 minutes a day. Repeat practice with new examples, not higher self-ratings alone.")
        for day in plan.to_dict("records"):
            with st.expander(f"Day {day['Day']} · {day['Focus']} · {day['Minutes']} min", expanded=day["Day"] == 1):
                st.write(day["Task"])
                st.write("**Done when:** " + day["Done when"])
        st.download_button("Download my seven-day plan", plan.to_csv(index=False), "path2placement-plan.csv", "text/csv")
    with tabs[2]:
        explain_score(result)
    st.divider()
    st.caption("This is not a probability of placement. The criteria and thresholds are design choices, not validated employability boundaries. Self-ratings, missing tests, opportunity differences and unmeasured factors affect the score. Your worth and potential are not a number.")
    if st.button("Update my answers"):
        st.session_state["step"] = 0
        go_page("assess")


def explain_score(result):
    st.write("Every input is normalized to 0–100. The overall score is the weighted average of the five category scores. Optional missing inputs are excluded only within their category.")
    df = pd.DataFrame([{"Category": cat, "Weight": f"{w:.0%}", "Category score": result["categories"][cat], "Contribution": round(w * result["categories"][cat], 2)} for cat, w in CATEGORY_WEIGHTS.items()])
    st.dataframe(df, hide_index=True, width="stretch")
    st.caption("Calculation uses full precision, rounded once at the end. Displayed contributions may differ by 0.01 due to rounding. All category weights and input thresholds are documented in About.")


def progress():
    header("A record of your effort", "My progress", "Compare your own assessments over time. This workspace contains only results you chose to save.")
    records = history()
    if not records:
        st.info("Your starting line is waiting. Complete an assessment and choose Save assessment to begin your history.")
        if st.button("Take an assessment", type="primary"):
            go_page("assess")
        return
    latest = records[-1]
    previous = records[-2] if len(records) > 1 else None
    a, b, c = st.columns(3)
    a.metric("Latest readiness score", f"{latest['score']:.1f}/100", f"{latest['score'] - previous['score']:+.1f} vs previous" if previous else None)
    b.metric("First assessment", f"{records[0]['score']:.1f}/100")
    c.metric("Saved assessments", len(records))
    if len(records) > 1:
        df = pd.DataFrame({"Assessment": list(range(1, len(records)+1)), "Score": [r["score"] for r in records], "Timestamp (UTC)": [r["created_at"] for r in records]})
        fig = px.line(df, x="Assessment", y="Score", markers=True, color_discrete_sequence=[GREEN], hover_data=["Timestamp (UTC)"])
        fig.update_yaxes(range=[0, 100], title="Readiness / 100")
        fig.update_xaxes(dtick=1)
        st.plotly_chart(chart_theme(fig, 300), width="stretch", theme=None, config={"displayModeBar": False})
        st.subheader("What changed since the previous assessment?")
        diff = pd.DataFrame([{"Category": cat, "Previous": previous["categories"][cat], "Latest": latest["categories"][cat], "Change": round(latest["categories"][cat] - previous["categories"][cat], 2)} for cat in CATEGORIES])
        st.dataframe(diff, hide_index=True, width="stretch")
        if latest.get("missing_optional") != previous.get("missing_optional") or latest["scoring_version"] != previous["scoring_version"]:
            st.warning("Optional-input coverage or scoring version changed. The score difference is not a like-for-like measure of improvement.")
    else:
        st.caption("One honest baseline saved. Save another assessment when your preparation changes to see a trend and category differences.")
    st.subheader("Assessment history")
    table = pd.DataFrame([{"Assessment": i+1, "Timestamp (UTC)": r["created_at"][:19].replace("T", " "), "Score / 100": r["score"], "Readiness band": r["band"], "Optional values missing": len(r["missing_optional"])} for i, r in enumerate(records)])
    st.dataframe(table.iloc[::-1], hide_index=True, width="stretch")
    st.download_button("Export assessment history · CSV", export_csv(records), "path2placement-history.csv", "text/csv", type="primary")
    with st.expander("Inspect a saved assessment"):
        chosen = st.selectbox("Assessment", range(len(records)), format_func=lambda i: f"#{i+1} · {records[i]['created_at'][:19]} UTC · {records[i]['score']:.1f}/100", index=len(records)-1)
        record = records[chosen]
        st.dataframe(pd.DataFrame({"Input": [FIELDS[k][0] for k in record["inputs"]], "Value": [str(v) if v is not None else "Not provided" for v in record["inputs"].values()]}), hide_index=True, width="stretch")
        st.plotly_chart(category_chart(record["categories"]), width="stretch", theme=None, config={"displayModeBar": False})
    st.divider()
    with st.expander("Delete this workspace’s history"):
        st.caption("Deletes only this workspace's saved assessments from the active SQLite database. Server backups, if any, are outside this app's control. Your current unsaved form is not deleted.")
        confirm = st.checkbox("I understand this cannot be undone", key="confirm_clear")
        if st.button("Permanently clear my history", disabled=not confirm):
            try:
                HistoryStore().clear(st.session_state["workspace_key"])
                st.session_state.pop("saved_id", None)
                st.rerun()
            except HistoryError as exc:
                st.error(str(exc))
    st.caption("Local history belongs to this workspace key. Hosting restarts may erase the database on ephemeral storage. Export records you want to keep.")


@st.cache_resource
def lab_model():
    return load_model()


def model_insights():
    header("The learning lab", "Model insights", "A reproducible machine-learning workflow, kept deliberately separate from your readiness assessment.")
    st.warning("Synthetic data only. These are simulated interview-exercise outcomes—not real students, real placements, or a probability of getting hired.")
    try:
        pipeline, meta = lab_model()
    except ModelError as exc:
        st.error(str(exc))
        st.code("python -m src.train_model --generate", language="bash")
        if st.button("Retry loading artifacts"):
            lab_model.clear()
            st.rerun()
        return
    st.subheader("What the data represents")
    st.write(meta["dataset"])
    st.write(meta["target_definition"])
    a, b, c = st.columns(3)
    a.metric("Usable simulated rows", meta["audit"]["usable_observations"])
    b.metric("Training / held-out rows", f"{meta['training_rows']} / {meta['test_rows']}")
    c.metric("Random seed", meta["seed"])
    st.caption(f"Trained {meta['trained_at_utc'][:10]} UTC · Scikit-learn {meta['sklearn_version']} · Artifacts are loaded, not retrained on interaction.")
    tabs = st.tabs(["Evaluation", "Data & workflow", "Try simulated inference"])
    with tabs[0]:
        st.subheader("Model comparison · training-set validation")
        comp = pd.DataFrame(meta["comparison"])[["model", "cv_f1_mean", "cv_f1_std"]].rename(columns={"model":"Model", "cv_f1_mean":"5-fold F1 mean", "cv_f1_std":"F1 standard deviation"})
        st.dataframe(comp, hide_index=True, width="stretch")
        st.write(f"**Selected: {meta['model_name']}** · Highest mean stratified cross-validation F1 on training rows only. The held-out partition did not select the winner.")
        st.subheader("Selected model · held-out synthetic test set")
        cols = st.columns(4)
        for col, metric in zip(cols, ["accuracy", "precision", "recall", "f1"]):
            col.metric(metric.title(), f"{meta['test_metrics'][metric]:.3f}")
        left, right = st.columns(2, gap="large")
        with left:
            st.markdown("#### Confusion matrix")
            fig = go.Figure(go.Heatmap(z=meta["test_metrics"]["confusion_matrix"], x=["Predicted fail", "Predicted pass"], y=["Actual fail", "Actual pass"], colorscale=[[0,"#EDF1E8"],[1,GREEN]], texttemplate="%{z}", showscale=False))
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(chart_theme(fig, 270), width="stretch", theme=None, config={"displayModeBar": False})
        with right:
            st.markdown("#### Class distribution · full dataset")
            counts = meta["audit"]["class_distribution"]
            fig = px.bar(x=["Simulated fail", "Simulated pass"], y=[counts.get("0", 0), counts.get("1", 0)], color_discrete_sequence=[GREEN], labels={"x":"", "y":"Observations"}, text_auto=True)
            st.plotly_chart(chart_theme(fig, 270), width="stretch", theme=None, config={"displayModeBar": False})
        st.caption("Accuracy: fraction correct. Precision: fraction of predicted passes that pass. Recall: fraction of simulated passes detected. F1: harmonic mean of precision and recall. F1 is the selection metric so accuracy is not the only criterion.")
        st.caption("False positive: a simulated failure predicted as a pass. False negative: a simulated pass predicted as a failure. These concepts must not be interpreted as actual hiring decisions.")
        st.subheader("Permutation importance · held-out F1 drop")
        importance = pd.DataFrame(meta["permutation_importance"]).sort_values("mean")
        fig = px.bar(importance, x="mean", y="feature", orientation="h", error_x="std", color_discrete_sequence=[GREEN], labels={"mean":"Mean F1 drop after shuffling", "feature":""})
        st.plotly_chart(chart_theme(fig, 290), width="stretch", theme=None, config={"displayModeBar": False})
        st.caption("Eight shuffles per feature; error bars show standard deviation. Negative values are possible. Correlations can distribute importance across features; importance does not establish causation.")
    with tabs[1]:
        st.markdown("""#### How simulated data is made
A shared normal latent preparation variable creates correlated CGPA, ratings and aptitude. Coding practice uses a capped gamma distribution. Internship is sampled separately. A documented logistic formula combines those features; labels are sampled from a Bernoulli distribution, so outcomes are intentionally noisy. About 3.5% missingness is introduced in aptitude and communication after labeling.

#### The workflow
1. Validate schema, feature ranges and binary labels. Remove duplicate predictor rows before splitting.
2. Hold out 20% with stratification and seed 42.
3. Fit median imputation, scaling and one-hot encoding **inside each training fold** using a `ColumnTransformer` and `Pipeline`.
4. Compare Logistic Regression, a depth-limited Decision Tree and a Random Forest with five-fold stratified F1.
5. Fit the selected pipeline on all training rows. Evaluate once on the untouched holdout.
6. Save a trusted Joblib pipeline, schema, checksum, library version and measured metrics.

No feature contains an outcome, salary, offer status or other future information. Swapping in real data requires reviewing its provenance, permissions, target meaning and known-at-prediction-time features—not just renaming a file.
""")
        st.write("**Missing values and duplicate audit**")
        st.json(meta["audit"])
        st.write("**Predictor schema:** " + ", ".join(meta["features"]))
        st.code("python -m src.train_model --generate", language="bash")
    with tabs[2]:
        st.write("Exercise the saved pipeline with an illustrative row. This result is not added to readiness history and is not a placement prediction.")
        with st.form("lab_inference"):
            a, b = st.columns(2)
            with a:
                cgpa = st.number_input("Illustrative CGPA", 0., 10., 7., .1)
                coding = st.number_input("Illustrative coding practice", 0, 500, 80)
                dsa = st.slider("Illustrative DSA rating", 1, 5, 3)
                quality = st.slider("Illustrative project quality", 1, 5, 3)
            with b:
                aptitude = st.number_input("Illustrative aptitude %", 0., 100., 60.)
                communication = st.slider("Illustrative communication", 1, 5, 3)
                internship = st.selectbox("Illustrative internship", ["none", "completed"])
            submit = st.form_submit_button("Run simulated inference", type="primary")
        if submit:
            frame = pd.DataFrame([{"cgpa":cgpa, "coding_practice":coding, "dsa_rating":dsa, "project_quality":quality, "aptitude":aptitude, "communication":communication, "internship":internship}])
            try:
                pred = predict_simulated(frame, pipeline)[0]
                st.info(f"Simulated exercise class: {'pass' if pred else 'fail'}. Educational pipeline output only—not an employment forecast.")
            except ValueError as exc:
                st.error(str(exc))
    st.divider()
    st.subheader("Limitations worth keeping in view")
    for limitation in meta["limitations"]:
        st.write("— " + limitation)


def about():
    header("Built for clarity, not certainty", "About Path2Placement", "A practical, explainable engineering portfolio project for students preparing for internships and campus placements.")
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        st.subheader("A useful question, answered honestly")
        st.write("‘What should I work on next?’ is more useful than an unsupported hiring probability. Path2Placement organizes five parts of preparation into a repeatable self-assessment, evidence-based practice tasks and personal progress history.")
        st.subheader("Two different systems")
        st.write("**Readiness assessment:** deterministic, adjustable criteria. No model is used to calculate your score or recommendations.")
        st.write("**ML learning lab:** three trained classifiers on explicitly simulated data. It demonstrates preprocessing, validation, evaluation and inference—not real placement forecasting.")
    with right:
        st.markdown('''<div class="side-panel"><div class="eyebrow">Under the hood</div><h3>Simple tools. Clear boundaries.</h3><p>Python 3.11 · Streamlit<br>Pandas · NumPy · Scikit-learn<br>Plotly · Joblib · SQLite · Pytest</p><div class="line"></div><p>No paid API. No external LLM.<br>No student rankings.<br>No invented success stories.</p></div>''', unsafe_allow_html=True)
    st.divider()
    st.subheader("The scoring methodology")
    st.write(f"Version {SCORING_VERSION}. Category weights sum to 100%. All thresholds and weights are product-design choices, not scientifically validated boundaries.")
    for category, weights in CATEGORY_FIELDS.items():
        with st.expander(f"{category} · {CATEGORY_WEIGHTS[category]:.0%} overall weight"):
            rows = []
            for key, weight in weights.items():
                label, low, high, _, optional, cap = FIELDS[key]
                rows.append({"Input": label, "Within category": f"{weight:.0%}", "Normalization to 100": f"min(value / {cap}, 1) × 100" if cap else f"(value − {low:g}) / {high-low:g} × 100", "Optional": "Yes" if optional else "No"})
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.write("1–5 ratings map to 0, 25, 50, 75, 100. CGPA is multiplied by 10; test percentages already use 0–100. A completed internship contributes at most 1.25 points overall. Project quality has more weight than project count. Optional missing tests are excluded and remaining weights rescaled within that category; this can change comparability, so the app flags it.")
    st.write("**Readiness bands:** 0–<40 Foundation Building · 40–<60 Developing · 60–<75 Progressing Toward Readiness · 75–<90 Nearly Ready · 90–100 Strong Preparation. Bands use the exact score, not its whole-number display.")
    st.subheader("Privacy & responsible use")
    st.write("No names, email addresses or sensitive demographic attributes are needed. SQLite stores input values, UTC timestamps, scores and coaching summaries only when you save. Each workspace uses a random recovery key hashed before storage. Keys are not placed in URLs. This is a prototype—not enterprise authentication. Anyone holding your key, and server administrators, can access your history. A fresh browser session creates a new workspace unless you restore a key. Keep the key private, export what matters and clear history when finished.")
    st.write("Self-ratings are subjective. Access to internships, mentoring and equipment is unequal. Synthetic data cannot represent these differences or establish fairness. Do not use this tool for hiring, admission, ranking students, or high-stakes decisions.")
    st.subheader("What comes next")
    st.write("Useful next steps are validated skill quizzes, feedback from students, configurable career tracks and a consented, licensed real dataset with external and subgroup evaluation. Hosted accounts, secure backups and stronger authentication would require a separate privacy and security design.")
    st.caption("See README.md, data/README.md, reports/model_evaluation.md and docs/PORTFOLIO.md for setup, data generation, measured evaluation and presentation notes.")
