# Course Project Problem Statement: CourseAgentAI
**Course:** `26ECAC401: Agentic AI`  
**Academic Year:** 2026  
**Artifact Name:** `CourseAgentAI — Course Project, Notes & Assignment Organizer`  
**Target Form Submission Link:** https://forms.gle/1aQtF42mfjiiaNPR7  
**Demo Evaluation Dates:** 23 November 2026 (First Seven Artifacts) & 24 November 2026 (Remaining Artifacts)  

---

## 1. Executive Summary & Problem Context

Higher education academic environments require continuous coordination across multiple fragmented domains:
1. **Course Knowledge & Syllabus Distribution:** Static lecture slides, PDF manuals, and lecture notes scattered across personal drives, LMS folders, and chat channels. Students struggle to locate grounded course facts, and search engines often retrieve ungrounded hallucinations.
2. **Assignment Administration & Verification:** Traditional LMS submission portals merely accept raw files or plain URL strings without verifying repository authenticity, leading to dead links, broken access permissions, and untracked late penalties.
3. **Evaluation Transparency & Similarity Detection:** Grading remains a labor-intensive, opaque bottleneck. Faculty lack automated tools to compute transparent pairwise submission similarity without claiming definitive plagiarism, or to derive objective draft scores strictly from published rubrics with mandatory human approval gates.
4. **Course Project Milestone Tracking:** Group project development requires tracking multi-stage milestones, member task distribution, deliverable uploads, and delay notifications in a unified dashboard.

Existing Learning Management Systems (LMS) act merely as passive file storage repositories. They lack **agentic intelligence**, **deterministic reliability**, and **multi-agent coordination**.

---

## 2. Core Project Objectives

The primary objective of **CourseAgentAI** is to build a fully integrated, intelligent course-management and learning platform powered by specialized agentic components and deterministic safety guardrails.

The platform unifies three primary academic pillars under a central **Course Coordinator Agent**:
- **Pillar 1: Intelligent Course Knowledge & Notes Repository** — Hierarchical document management system supporting 12 structured folders (`01_Notes` through `12_Other_Resources`), multi-format text extraction (PDF, DOCX, PPTX, TXT, MD, CSV), recursive indexing, and grounded BM25 / local semantic retrieval with verifiable citations.
- **Pillar 2: Verifiable Assignment Portal & Evaluation Workflow** — Real GitHub repository validation (syntax checks, DNS verification, public accessibility, rate-limit resilience), file upload security, persistent submission history, pairwise n-gram similarity analysis, rubric-based draft grading assistance, and faculty-governed publishing gates.
- **Pillar 3: Project Milestone & Activity Tracking** — Group and individual course project tracking with weighted milestone completion percentages, deliverable links, progress commentary, and activity timelines.

---

## 3. Detailed Functional Requirements

### 3.1 Course Knowledge Management System (DMS)
- **Folder Hierarchy:** Strictly maintain the 12 logical academic directories:
  ```text
  knowledge/
      01_Notes/ (Chapter_1 through Chapter_7)
      02_Lecture_Slides/
      03_Lab_Manuals/
      04_Lab_Reports/
      05_Lesson_Plans/
      06_Assignments/
      07_Question_Banks/
      08_Reference_Materials/
      09_Project_Documentation/
      10_Announcements/
      11_Study_Materials/
      12_Other_Resources/
  ```
- **Operations:** Recursive folder exploration, file upload with SHA-256 duplicate detection, file renaming, moving, secure deletion, and instant re-indexing.
- **Multi-Format Extraction:** Extract and index content from `.pdf` (pypdf), `.docx` (python-docx), `.pptx` (python-pptx), `.txt`, `.md`, and `.csv`.
- **Grounded Search:** Lexical BM25 and semantic embedding search returning exact document titles, section headers, character spans, and relevance scores.

### 3.2 Assignment Lifecycle & Verification Portal
- **Faculty Workflow:** Create, update, publish, and archive assignments with deadlines, maximum points, late-submission rules, and weighted multi-criterion rubrics.
- **Student Submission Validation:**
  - Real GitHub URL validation: verify valid owner/repository pattern, ensure host is exactly `github.com` (prevent SSRF and lookalike domains), verify DNS reachability, and check public accessibility via HTTP HEAD/GET without claiming full source analysis if only accessibility was checked.
  - Safe file uploads: MIME-type validation, size restrictions (10 MB limit), path traversal sanitization, and storage isolation.
  - Submission Status Lifecycle: `SUBMITTED`, `LATE`, `UNDER_REVIEW`, `DRAFT_GRADED`, `APPROVED`, `PUBLISHED`, `RESUBMISSION_REQUESTED`.
- **Faculty Review & Approval Gate:**
  - Draft grades derived transparently from rubric criteria.
  - Faculty review interface with NO pre-filled scores (eliminating placeholder bias).
  - Explicit separation between draft saving and final publishing: unpublished draft grades remain strictly private to faculty; students only view grades once explicitly approved and published.

### 3.3 Submission Similarity Analysis
- Compute pairwise n-gram Jaccard similarity across student submissions and reference code.
- Report exact matching token percentages and identify flagged pairs (similarity $\ge 30\%$).
- Prominently include ethical limitation disclaimers: similarity scores represent textual overlap and never constitute autonomous proof of academic dishonesty; human faculty review is mandatory.

### 3.4 Multi-Agent Specialist Coordination
- **Course Coordinator Agent:** Analyzes incoming user requests, classifies intent, tracks task lifecycle, delegates to specialized agents, and handles retries safely.
- **10 Specialized Agent Roles:**
  1. *Course Coordinator Agent*
  2. *Notes Repository Agent*
  3. *Assignment Distribution Agent*
  4. *Submission Collection Agent*
  5. *Plagiarism / Similarity Agent*
  6. *Grading Assistance Agent*
  7. *Project Milestone Tracking Agent*
  8. *Faculty Review & Approval Workflow*
  9. *Grade Publishing & Archive Agent*
  10. *Research & Evidence Retrieval Component*

### 3.5 Enterprise Safety, Governance & Unified Audit Trail
- **Role-Based Access Control (RBAC):** Strict authentication using Argon2id password hashing and session tokens, enforcing STUDENT, FACULTY, and ADMIN permissions.
- **Persistent Proposal & Rollback:** High-consequence mutations require formal proposals in SQLite, faculty approval, and atomic one-click state rollback.
- **Unified Audit Log:** Append-only SQLite table (`audit_events`) recording timestamp, actor, role, resource, action, outcome, and request trace IDs across all academic operations.

---

## 4. Evaluation Criteria & Deliverables
1. **Assignments:** Complete source code, standalone execution runners, and passing automated test suites for all 12 laboratory assignments.
2. **Course Project Codebase:** Production-grade FastAPI backend, SQLite database migrations, and responsive Apple Cupertino-inspired UI.
3. **Problem Statement & Final Report:** Formal academic documentation articulating the problem, architecture, implementation, experimental results, and demo guide.
4. **Repository Structure:** Formally structured Git repository ready for ownership transfer to the designated GitHub organization.
