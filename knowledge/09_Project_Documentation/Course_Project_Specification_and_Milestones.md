# Course Project Specification: CourseAgentAI
Course: 26ECAC401: Agentic AI
Academic Year: 2026

## 1. Project Overview & Problem Statement
Academic course administration is heavily fragmented across static syllabus PDFs, disconnected LMS folders, manual assignment grading, and ungrounded chat assistants. CourseAgentAI unifies these domains into a governed, agentic learning and course-management operations platform.

## 2. Core Subsystems
1. **Course Knowledge & Notes Management:** Hierarchical multi-folder document management system with recursive indexing and high-precision BM25 retrieval.
2. **Assignment Distribution & Submission Portal:** Verifiable student GitHub and file submissions with anti-SSRF validation, attempt versioning, and student isolation.
3. **Transparent Evaluation & Similarity Review:** Pairwise n-gram submission similarity reports, rubric-based draft grading assistance, and faculty approval gates.
4. **Course Project & Milestone Tracker:** Individual and group project progress calculation, deliverable submission, and activity timeline.
5. **Specialized Agent Coordination:** Central coordinator delegating to Notes, Distribution, Submission, Similarity, Grading, and Milestone agents.

## 3. Milestones & Timeline
- **Milestone 1 (Week 4):** Problem Statement, Entity Architecture, and Database Schema Sign-off.
- **Milestone 2 (Week 8):** Governed Knowledge RAG Ingestion & 9 ReAct Tools Implementation.
- **Milestone 3 (Week 12):** 10-Node Specialist DAG, Parallel Swarm, and Submissions Workflow.
- **Milestone 4 (Week 16):** Final Capstone Defense, Complete Submission Package, and Regression Report.