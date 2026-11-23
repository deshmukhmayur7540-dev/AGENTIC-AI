# Agentic AI Comprehensive Question Bank & Practice MCQs
Course: 26ECAC401: Agentic AI

## Section A: Multiple Choice Questions (MCQs)

1. What constitutes the core autonomous loop of an Agentic AI system?
   - A) Prompt -> Completion
   - B) Plan -> Act -> Observe -> Revise [CORRECT]
   - C) Fine-tune -> Quantize -> Evaluate
   - D) Scrape -> Clean -> Embed
   Explanation: Chapter 1 establishes that autonomous agents differ from passive chatbots by continuously observing environment feedback and revising plans.

2. In the ReAct architectural pattern, what does the agent record at each step?
   - A) Only final answers
   - B) Thought, Action, Observation [CORRECT]
   - C) Loss gradients and weights
   - D) Token probabilities
   Explanation: Chapter 2 details ReAct as interleaving reasoning (Thought), tool invocation (Action), and environment response (Observation).

3. Why is lexical retrieval alone insufficient to establish claim verification in Deep Research?
   - A) Lexical search is too slow
   - B) Lexical matching finds word overlap but does not verify semantic entailment [CORRECT]
   - C) Word embeddings are required for all databases
   - D) Lexical search always hallucinates citations
   Explanation: Chapter 4 and Lab 9 demonstrate that candidate passage retrieval requires human or entailment verification to prevent false claims.

4. What is the primary purpose of state checkpointing in an agent runtime?
   - A) To compress memory
   - B) To allow resumption from the last valid step without re-executing completed work [CORRECT]
   - C) To bypass authentication gates
   - D) To speed up LLM generation
   Explanation: Chapter 6 emphasizes fault tolerance and crash resilience through serialized state checkpoints.

5. What does the Model Context Protocol (MCP) standardize?
   - A) Neural network architectures
   - B) Client-server interfaces between AI agents and external tools/data sources [CORRECT]
   - C) GPU cluster scheduling
   - D) Frontend React components
   Explanation: Chapter 5 details MCP as a secure, typed protocol connecting agents to heterogeneous sources.

## Section B: Analytical & Architectural Questions

1. Compare Directed Acyclic Graphs (DAGs) and Parallel Swarms: Detail when sequential state passing is required versus when asynchronous scatter-gather fan-out provides superior throughput.
2. Explain Defense-in-Depth for Assignment Submissions: Why is regex URL validation alone inadequate, and how do hostname whitelisting, SSRF target blocking, and remote repository accessibility checks protect academic integrity?
3. Analyze Consequential Human-in-the-Loop Gates: Describe how an agent runtime should pause before high-impact operations (e.g. grade publication) and verify faculty authority.