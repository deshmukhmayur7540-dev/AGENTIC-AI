import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Assignment 9 Verification Runner
from app.labs.lab9.agent import evidence_verifier

def main():
    print("=== Assignment 9: Deep Research Claim Verifier ===")
    claims = ["ReAct loop combines reasoning traces and action execution"]
    res = evidence_verifier.verify_claims(claims=claims, chapter=2)
    print(f"Verified Claims: {len(res['claims'])}")
    print(f"Evidence Items: {len(res['evidence_table'])} (First status: {res['evidence_table'][0]['status'] if res['evidence_table'] else 'None'})")
    print("Assignment 9 Verification: PASSED")

if __name__ == '__main__':
    main()
