"""The single source of truth for readiness criteria (product choices, not research)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = 42
SCORING_VERSION = "1.0"
CATEGORY_WEIGHTS = {
    "Academic preparation": 0.15,
    "Programming & DSA": 0.30,
    "Projects & experience": 0.25,
    "Aptitude & communication": 0.15,
    "Interview & resume": 0.15,
}
# field: label, minimum, maximum, default, optional, count cap (None = linear)
FIELDS = {
    "cgpa": ("Current CGPA · out of 10", 0., 10., 7., False, None),
    "consistency": ("Academic consistency", 1, 5, 3, False, None),
    "core": ("Core subjects · DBMS, OOP, OS & networks", 1, 5, 3, False, None),
    "languages": ("Programming languages you can use independently", 0, 30, 1, False, 3),
    "programming": ("Programming proficiency", 1, 5, 3, False, None),
    "dsa": ("Data structures & algorithms", 1, 5, 2, False, None),
    "problems": ("Coding problems solved and understood", 0, 100000, 30, False, 250),
    "projects": ("Completed technical projects", 0, 1000, 1, False, 3),
    "demos": ("Projects with a working demonstration", 0, 1000, 0, False, 2),
    "documented": ("Projects with documented source code / GitHub", 0, 1000, 0, False, 2),
    "quality": ("Project implementation & understanding", 1, 5, 2, False, None),
    "internship": ("Internship experience", 0, 1, 0, False, None),
    "aptitude": ("Aptitude practice test · %", 0., 100., 50., False, None),
    "reasoning": ("Logical reasoning practice test · % (optional)", 0., 100., None, True, None),
    "communication": ("Communication skills", 1, 5, 3, False, None),
    "explanation": ("Explaining technical concepts", 1, 5, 3, False, None),
    "mock": ("Mock interview · % (optional)", 0., 100., None, True, None),
    "resume": ("Resume readiness", 1, 5, 2, False, None),
    "interview": ("Interview preparation", 1, 5, 2, False, None),
    "project_confidence": ("Confidence explaining your projects", 1, 5, 2, False, None),
}
# Within-category weights sum to 1. Optional missing inputs are excluded and
# remaining weights rescaled ONLY inside that category.
CATEGORY_FIELDS = {
    "Academic preparation": {"cgpa": .45, "consistency": .20, "core": .35},
    "Programming & DSA": {"languages": .10, "programming": .30, "dsa": .40, "problems": .20},
    "Projects & experience": {"projects": .10, "demos": .20, "documented": .15, "quality": .50, "internship": .05},
    "Aptitude & communication": {"aptitude": .35, "reasoning": .15, "communication": .25, "explanation": .25},
    "Interview & resume": {"mock": .25, "resume": .30, "interview": .25, "project_confidence": .20},
}
BANDS = [(40, "Foundation Building"), (60, "Developing"),
         (75, "Progressing Toward Readiness"), (90, "Nearly Ready"),
         (101, "Strong Preparation")]
SECTION_HELP = {
    "Academic preparation": "A snapshot of your studies, not a measure of your potential. Rate core subjects across DBMS, OOP, operating systems and networks.",
    "Programming & DSA": "Count problems you understand, not just submissions. Counts are capped so quantity cannot overwhelm practical skill.",
    "Projects & experience": "One well-understood, working project can be more useful than many unfinished ones. No internship is a valid starting point.",
    "Aptitude & communication": "Use a recent practice-test result. Communication ratings are self-assessments, not objective test scores.",
    "Interview & resume": "Be honest about what you can explain and demonstrate. Leave the mock score blank if you have not taken one.",
}
