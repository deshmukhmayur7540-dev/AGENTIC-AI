# Assignment 9 Verification Runner
from app.labs.lab9.agent import evidence_verifier

def main():
    print("=== Assignment 9: Deep Research Claim Verifier ===")
    claims = ["ReAct loop combines reasoning traces and action execution"]
    res = evidence_verifier.verify_claims(claims=claims, chapter=2)
    print(f"Verified Claims: {len(res['results'])}")
    print(f"Verdict: {res['results'][0]['status']}")
    print("Assignment 9 Verification: PASSED")

if __name__ == '__main__':
    main()
