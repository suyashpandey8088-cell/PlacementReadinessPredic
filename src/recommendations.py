"""Input-linked, deterministic coaching; no external LLM or paid service."""
from src.readiness_scoring import assess

# category, trigger field(s), title, action, measurable completion
RULES = [
    ("Programming & DSA", "dsa", "Build a DSA routine", "Practice arrays, strings and basic searching. Solve two appropriately leveled problems and review errors.", "Two solutions explained with time complexity"),
    ("Programming & DSA", "programming", "Strengthen programming fundamentals", "Choose one language. Write a small program using functions, collections and error handling.", "One runnable program with three test cases"),
    ("Projects & experience", "quality", "Make one project demonstrable", "Choose a small, useful problem. Build a working vertical slice and explain one architecture trade-off.", "A working demo and a short architecture note"),
    ("Projects & experience", "documented", "Document your work", "Add a README with setup steps, the problem, implementation and honest results. Verify the repository links.", "A peer can run the project from the README"),
    ("Academic preparation", "core", "Revisit core subjects", "Revise DBMS, OOP, operating systems and networks. Explain one concept from each without notes.", "Four explanations and a ten-question self-quiz"),
    ("Academic preparation", "cgpa", "Create a subject revision loop", "Pick one difficult subject, revise a short topic and solve five practice questions. Review mistakes.", "Five attempted questions and a mistake log"),
    ("Aptitude & communication", "aptitude", "Practice aptitude deliberately", "Do a short timed quantitative and reasoning set. Categorize mistakes before attempting similar questions.", "Ten questions, accuracy recorded, two mistakes reviewed"),
    ("Aptitude & communication", "communication", "Explain an idea out loud", "Record a two-minute technical explanation. Listen for structure, clarity and unsupported claims.", "One recording with three specific improvements"),
    ("Interview & resume", "resume", "Make your resume verifiable", "Rewrite a project bullet using problem, implementation and result. Remove unsupported claims and check all links.", "Three revised bullets and every link checked"),
    ("Interview & resume", "interview", "Rehearse an interview", "Run a short mock interview with a peer. Include a project walkthrough and a question about trade-offs.", "A 20-minute mock and three feedback notes"),
]


def recommend(inputs):
    result = assess(inputs)
    data = result["inputs"]
    actions = []
    for category, field, title, task, criterion in RULES:
        value = data[field]
        triggered = (value < 3 if field in ("dsa", "programming", "quality", "core", "communication", "resume", "interview")
                     else value < 1 if field == "documented" else value < 60 if field == "aptitude" else value < 6)
        if triggered:
            actions.append({"title": title, "category": category,
                            "reason": f"{field.replace('_', ' ').title()} is {value:g}; this category scores {result['categories'][category]:.0f}/100.",
                            "task": task, "criterion": criterion, "priority": "Priority", "field": field})
    # Cover categories missed by specific rules (e.g. low mock or explanation scores).
    for category, score in result["categories"].items():
        if score < 75 and not any(a["category"] == category for a in actions):
            actions.append({"title": f"Practice: {category.lower()}", "category": category,
                            "reason": f"This category scores {score:.0f}/100; review its lowest-rated inputs.",
                            "task": "Select the lowest-rated skill in this category. Complete a 25-minute practice session, then review your mistakes.",
                            "criterion": "One practice artifact and three feedback notes", "priority": "Priority", "field": None})
    actions.sort(key=lambda a: (result["categories"][a["category"]], a["title"]))
    if not actions:
        actions.append({"title": "Maintain preparation with feedback", "category": "Interview & resume",
                        "reason": "Every category is at least 75/100. External feedback can check self-ratings.",
                        "task": "Ask a peer to review a project and run a timed mock interview. Focus on depth rather than adding counts.",
                        "criterion": "One peer review and two targeted improvements", "priority": "Optional enhancement", "field": None})
    return actions


def seven_day_plan(inputs):
    actions = recommend(inputs)[:3]
    plan = []
    for day in range(1, 7):
        action = actions[(day - 1) % len(actions)]
        plan.append({"Day": day, "Focus": action["title"],
                     "Task": action["task"] if day <= 3 else "Repeat with a new example. " + action["task"],
                     "Minutes": 35 if day <= 3 else 45, "Done when": action["criterion"]})
    plan.append({"Day": 7, "Focus": "Review & reassess", "Task": "Review your evidence and mistake log. Reassess honestly; do not increase ratings without new evidence.",
                 "Minutes": 30, "Done when": "One saved assessment and a note on what changed"})
    return plan
