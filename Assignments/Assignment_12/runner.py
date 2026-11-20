# Assignment 12 Verification Runner
from app.labs.lab12.governance import governed_change_store

def main():
    print("=== Assignment 12: Enterprise Safety & Governance ===")
    proposals = governed_change_store.list()
    print(f"Existing Proposals: {len(proposals)}")
    sample = governed_change_store.propose(
        resource_id="sample-rubric-config",
        current_value={"weight": 20},
        proposed_value={"weight": 25},
        summary="Adjust rubric weight for Lab 12"
    )
    print(f"Created Proposal: {sample['proposal_id']}, Status: {sample['status']}")
    decided = governed_change_store.decide(sample['proposal_id'], approved=True, actor="faculty-lead")
    print(f"Decided Proposal: {decided['status']}")
    rolled = governed_change_store.rollback(sample['proposal_id'], actor="faculty-lead")
    print(f"Rolled Back: {rolled['status']}")
    print("Assignment 12 Verification: PASSED")

if __name__ == '__main__':
    main()
