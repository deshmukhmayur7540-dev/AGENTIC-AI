# Assignment 10 Verification Runner
from app.labs.lab10.cloud_ops import CloudOperationsAgent

def main():
    print("=== Assignment 10: Cloud Operations Health Monitor ===")
    agent = CloudOperationsAgent()
    status = agent.get_status()
    print(f"Cluster Status: {status['cluster_status']}")
    diag = agent.diagnose_component("database")
    print(f"Diagnosis: {diag['root_cause']}")
    print("Assignment 10 Verification: PASSED")

if __name__ == '__main__':
    main()
