# Chapter 6: Controlled Agent Runtimes, Checkpointing & Resilient Execution
Course: 26ECAC401: Agentic AI
Academic Year: 2026

## 6.1 The Controlled Agent Runtime Paradigm
Autonomous agents operating in production academic or enterprise environments must not run as unbounded loops. The controlled agent runtime bounds execution using:
1. **Step Budget:** Strict maximum execution steps (e.g. max 10 steps per task).
2. **Execution Timeout:** Wall-clock duration bounds (e.g. 30 seconds max).
3. **State Checkpointing:** Serializing snapshot state after every atomic step.

## 6.2 Checkpointing and Crash Recovery
Every runtime step captures a `StateCheckpoint` containing run ID, step counter, working scratchpad, completed node outputs, and timestamp. If an unexpected runtime interruption or simulated crash occurs, the engine resumes directly from the latest valid checkpoint without re-running completed work or duplicating external side-effects.

## 6.3 Consequential Human-in-the-Loop Gates
Consequential actions (e.g. publishing final grades, dropping a course, or deploying infrastructure) trigger mandatory approval gates. The engine transitions to `WAITING_APPROVAL`, suspends execution safely, and proceeds only upon verified human faculty signature.