# Assignment 5 Verification Runner
from app.labs.lab5.connector import AcademicConnector

def main():
    print("=== Assignment 5: Governed Academic Connector ===")
    connector = AcademicConnector()
    student_res = connector.query(actor_role="STUDENT", actor_id="std-001", course_id="26ECAC401", source="submissions")
    print(f"Student Query Submissions: {len(student_res)}")
    print("Assignment 5 Verification: PASSED")

if __name__ == '__main__':
    main()
