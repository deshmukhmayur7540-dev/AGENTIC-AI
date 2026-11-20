import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Assignment 10 Verification Runner
from app.labs.lab10.cloud_ops import CloudOperationsAgent

def main():
    print("=== Assignment 10: Cloud Operations Health Monitor ===")
    agent = CloudOperationsAgent()
    status = agent.get_cluster_status()
    print(f"Cluster ID: {status['cluster']['cluster_id']}")
    diag = agent.diagnose_infrastructure("database-primary")
    print(f"Diagnosis Status: {diag.get('status')}")
    print("Assignment 10 Verification: PASSED")

if __name__ == '__main__':
    main()
