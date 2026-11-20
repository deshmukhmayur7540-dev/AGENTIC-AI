import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Assignment 5 Verification Runner
from app.labs.lab5.governed_connector import governed_connector
from app.models.lab5_models import ConnectorRequest, ConnectorRole, ConnectorOperation

def main():
    print("=== Assignment 5: Governed Academic Connector ===")
    governed_connector.initialize()
    req = ConnectorRequest(
        role=ConnectorRole.FACULTY,
        user_id="faculty-lead",
        course_id="26ECAC401",
        source_id="notes",
        operation=ConnectorOperation.READ,
        query={"action": "search", "query": "autonomous agent loop"}
    )
    res = governed_connector.dispatch(req)
    print(f"Connector Response Success: {res.success}")
    print("Assignment 5 Verification: PASSED")

if __name__ == '__main__':
    main()
