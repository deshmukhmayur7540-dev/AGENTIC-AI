import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Assignment 3 Verification Runner
from app.labs.lab3.registry import skill_registry

def main():
    print("=== Assignment 3: Reusable Academic Skills Registry ===")
    skills = skill_registry.list_skills()
    print(f"Registered Skills: {[s.name for s in skills]}")
    assert len(skills) >= 3, "Expected at least 3 skills"
    plan_skill = skill_registry.get_skill("course_planning_skill")
    assert plan_skill is not None
    print("Assignment 3 Verification: PASSED")

if __name__ == '__main__':
    main()
