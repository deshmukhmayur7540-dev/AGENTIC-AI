# Lab 4 Local Embedding Evaluation

> The Phase 1 section below is a historical evaluation-only snapshot. Its recommendation has since been tested and implemented; see the Phase 2 results at the end of this report.

**Phase:** 1 — evaluation only (historical snapshot)  
**Decision status:** Superseded by the measured Phase 2 result below  
**Scope:** Read-only inspection and model evaluation. No application source, dependency manifest, database, or model files were changed or created.

## Executive summary

Lab 4 already separates 24-hour SQLite-backed session state from explicitly saved, durable user memories. Explicit memories and prior-submission metadata are ranked with a local, token-based TF-IDF cosine implementation. Course documents and course materials continue to use the existing in-memory BM25 index. These are not semantic embeddings.

No embedding runtime is currently declared in `requirements.txt` or installed in the inspected Python environment. The project uses Python 3.12.10 on Windows 11, an Intel Core i5-12450H (8 cores / 12 logical processors), and approximately 15.7 GiB of physical RAM. `sentence-transformers`, `transformers`, `torch`, and `onnxruntime` are absent. No model was downloaded or benchmarked, so latency and process peak memory are not measured.

**Recommendation for Phase 2 review:** evaluate `sentence-transformers/all-MiniLM-L6-v2` first as the quality-oriented default candidate. It has a published 384-dimensional sentence-embedding interface and a repository-reported model-weight artifact of 90,868,376 bytes. `paraphrase-MiniLM-L3-v2` is a viable smaller alternative at 69,569,488 bytes, also 384 dimensions. The available evidence does not establish a head-to-head quality or CPU-latency result on CourseAgentAI data; a controlled local evaluation must do that before treating the recommendation as final.

## Existing implementation findings

| Area | Inspected implementation |
|---|---|
| Session state | `app/labs/lab4/session_store.py` stores session state and turns in SQLite, assigns an expiry (24 hours by default), cleans expired state during store operations, and supports clear/delete. |
| Durable user references | `app/labs/lab4/knowledge_store.py` writes explicit long-term references to `lab4_memory_records` with owner, course, title, content, tags, and timestamp. Session turns are not automatically copied into this table. |
| Similarity | The same module tokenizes text, computes TF-IDF-style weights, and ranks by cosine similarity. Responses label the method `local_tfidf_cosine_lexical` (or its submission-metadata variant) and explicitly state that embedding similarity is false. |
| Submission history | Prior submissions are selected by course and, for students, by the authenticated student's ID before ranking. Only assignment title/ID, repository name, stored notes, and status/validation labels are compared; repository contents are not fetched. Faculty course access is checked in `app/api/routes_lab4.py`. |
| Course-document retrieval | `app/knowledge/store.py` implements deterministic BM25; `app/knowledge/service.py` discovers, extracts, chunks, and indexes course documents and materials. Search results preserve source-document, location, course, chapter, tag, and material provenance. |
| Database | `app/data/db.py` creates the Lab 4 session, turn, and memory tables during explicit database initialization. There is no embedding table. No initialization or migration was run for this evaluation. |
| API | `app/api/routes_lab4.py` exposes authenticated session, course-document retrieval, saved-memory, similar-memory, and similar-submission routes. It checks course access before calling these stores. |
| Tests | `tests/test_lab4_memory.py` and `tests/test_lab4_api.py` cover session persistence/expiry, explicit-memory persistence and separation, tags, provenance, student/owner/course scoping, and the current lexical retrieval behavior. They do not prove semantic embedding quality or offline model execution. |
| Test database safety | `tests/conftest.py` sets `DATABASE_PATH` to a temporary test data directory before importing and initializing the database. Phase 2 tests must continue to use that disposable database (or another `tmp_path` database), never the governed database. |

### Environment and dependencies

The inspected `requirements.txt` contains the existing FastAPI, Pydantic, SQLite-adjacent application, and document-processing dependencies, but no sentence-transformer, Transformers, PyTorch, or ONNX Runtime package.

The current Python 3.12 environment has NumPy 2.5.4 and does not have the model runtime packages listed above. The PyPI project metadata for `sentence-transformers` currently lists Python 3.12 among supported classifiers. This is evidence of declared Python-version support, not a verified installation of a mutually compatible CPU dependency set in this project. Phase 2 should resolve and pin a compatible CPU-only dependency set in a clean disposable environment, and run import, inference, and dependency checks there before changing project manifests.

## Candidate comparison

Repository metadata below was read from the Hugging Face model API and model cards. Weight sizes are the exact `model.safetensors` file sizes advertised by the model repository at the revisions inspected; they are not full installation sizes. The model repositories also contain alternate framework exports, which should not all be downloaded for a CPU PyTorch deployment.

| Candidate | Parameters and dimensions | Model weight footprint | CPU/RAM and latency | Fit and caveats |
|---|---:|---:|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | Hugging Face safetensors metadata reports 22,713,216 F32 parameters plus 512 integer entries (22,713,728 total entries); model card reports 384-dimensional embeddings. The card says inputs beyond 256 word pieces are truncated. | Safetensors: **90,868,376 bytes** (about 86.6 MiB). This excludes tokenizer/config files, installed libraries, and runtime memory. | CPU-only inference is technically supported by the Sentence Transformers API (`device="cpu"`), and the model is small relative to current transformer models. Actual peak RAM and request latency are **unknown**; neither this machine nor this model was benchmarked. Runtime memory must exceed the weight-file size and includes framework, tokenizer, and activations. | Recommended first candidate for a quality-oriented evaluation: the model card specifically describes sentence/short-paragraph encoding for semantic search and similarity. The extra three transformer layers relative to L3 may improve representation quality but will likely increase computation; no project-specific quality or latency comparison is available to substantiate the size of either effect. |
| `sentence-transformers/paraphrase-MiniLM-L3-v2` | Hugging Face safetensors metadata reports 17,389,824 F32 parameters plus 512 integer entries (17,390,336 total entries); model card reports 384-dimensional embeddings. Its published architecture has a 128-token maximum sequence length. | Safetensors: **69,569,488 bytes** (about 66.3 MiB). This excludes tokenizer/config files, installed libraries, and runtime memory. | CPU-only inference is technically supported by the same API. Actual peak RAM and latency are **unknown** and were not measured. Its smaller weight artifact suggests a lower model-storage requirement, not a proven end-to-end memory or latency result. | Suitable alternative if model footprint or CPU compute is the priority. It has three transformer layers and a shorter published sequence length. Its semantic quality for this project's course notes and submissions has not been evaluated. |

Neither candidate is multilingual according to the model metadata (English); the course-library language distribution should be confirmed before treating either as sufficient.

### Downloads, model versions, and licensing

| Candidate | Repository revision inspected | Model-card license metadata |
|---|---|---|
| `all-MiniLM-L6-v2` | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | Apache-2.0 |
| `paraphrase-MiniLM-L3-v2` | `4ca70771034acceecb2e72475f72050fcdde4ddc` | Apache-2.0 |

Both Hugging Face model cards declare Apache-2.0. This is the model repository's stated license metadata, not legal advice or a determination about rights associated with training datasets or other upstream components. Before distribution, retain the exact model revision and license text/notice applicable to the downloaded files and review the licenses of installed runtime dependencies.

The Sentence Transformers API documents loading a model from a local filesystem path, `device="cpu"`, `local_files_only=True`, and `trust_remote_code=False` (the default). Hugging Face documents offline mode through pre-caching model files and setting `HF_HUB_OFFLINE=1`. Thus inference can be offline after the model files and dependencies have been installed locally. This was verified from library documentation, not exercised locally because the packages and models are not installed.

## Integration recommendation

Keep the current SQLite records authoritative and add derived embedding data without copying source text into a vector store.

### Storage

For the first implementation, use a small, model-specific embedding table for each eligible source type (saved memories and submission metadata), with a source-record foreign key and `ON DELETE CASCADE`. This avoids a polymorphic reference that SQLite cannot enforce with a normal foreign key. Each embedding row should include:

- Source record ID, owner ID, and course ID (or a join to obtain and validate them).
- Model repository ID and immutable model revision/commit.
- Embedding dimension and a vector serialization/version marker.
- SHA-256 hash of the exact normalized text sent to the encoder.
- A float32 vector stored as a compact binary blob (384 values require 1,536 bytes before row overhead), not another copy of source content.
- Creation and last-update timestamps.

Use one current embedding per source/model configuration (unique source key and model revision, or replace the source row when the configured revision changes). Reuse it only when the text hash, model revision, and dimension all match. Re-embed when any of these differ. Delete/replace paths should remove or invalidate the associated row in the same transaction as the source change wherever the existing service owns both operations. Do not silently leave stale vectors after source deletion.

SQLite does not provide native vector nearest-neighbor search in the current project. For the existing small workload, select eligible candidate rows in SQL first, then compute cosine similarity in process. Add measurements and a documented scale threshold before considering a local vector index extension. Do not rank all students' records and filter unauthorized results afterward.

### Indexing and authorization

1. Authenticate and authorize the requested course before embedding the query.
2. Select candidates with SQL predicates for course and source ownership before loading vectors or calculating scores. Student queries must include the authenticated `student_id`; saved memories must include authenticated `user_id`. Faculty queries may include only the already authorized course.
3. Generate query embeddings with one lazily initialized CPU model instance. Keep the model revision and tokenizer/model path fixed by configuration.
4. Compute cosine similarity against the scoped candidate set, apply an explicit configurable minimum score and bounded result limit, then return the existing source IDs, titles, timestamps, tags, and citations.
5. Use a batch indexing/rebuild command for existing eligible rows. Process bounded batches, use transactions per batch, report counts/errors, and never run automatically at application import or normal startup.
6. On model or input change, re-embed idempotently; avoid duplicate rows for unchanged inputs. On source replacement or deletion, invalidate/delete the previous vector.

For candidate sizing, SQLite linear scan is a reasonable initial, measurable baseline rather than a claim of scalable vector search. Any later course-wide document embedding work should separately review access controls for materials, source metadata, replacement, and deletion before being included.

### Local model setup and offline behavior

If Phase 2 is approved, pin the selected repository to its inspected commit and explicitly download it into a project-configured model directory (for example, `models/lab4/all-MiniLM-L6-v2`) using a setup command. Do not resolve a Hub model name at application startup. At inference, load only from that local directory with CPU device, `local_files_only=True`, and remote code disabled; set offline mode for the model process or integration test. Missing/corrupt model files should yield an explicit unavailable status/error and preserve the existing lexical/BM25 behavior as an explicitly labeled fallback.

The project has no observed model CPU/RAM benchmark. Do not make a RAM or latency promise based only on the parameter count or artifact size. Measure startup load time, peak resident memory, and single-query and batched CPU latency on representative course text on the target host before documenting operational sizing.

## Measurable acceptance criteria for Phase 2

1. A real pinned local model produces 384-dimensional, finite vectors on CPU; if vectors are normalized, their norms are within a documented tolerance.
2. A deterministic local semantic fixture includes paraphrases with deliberately different key vocabulary. With the actual model, the related record ranks above unrelated controls. Record the model revision, inputs, scores, thresholds, and measured outcome; do not make a semantic-quality claim from mocked vectors.
3. The test verifies the configured local directory is used and fails clearly when files are missing/corrupt. Normal application startup does not download or load a model.
4. An explicitly invoked model setup/rebuild procedure is the only supported network-enabled step. An offline integration test with network access blocked successfully loads the pre-downloaded model and performs inference.
5. Embeddings persist across store recreation; unchanged content/model does not create duplicates; changed content or revision replaces the stale vector; source deletion removes its vector.
6. Student candidate selection is restricted in SQL to that student's records and course before ranking. Faculty candidate selection is restricted to the authorized course. Tests prove that unauthorized rows are not loaded/ranked, not just omitted from the final response.
7. Results retain real source provenance, use a configured result cap and threshold, and describe scores as cosine similarity—not plagiarism probabilities.
8. The existing lexical TF-IDF and BM25 modes and their current response contracts remain available and pass regression tests. Hybrid scoring is not introduced unless an explicit formula, normalization, and tests justify it.
9. Unit tests use a deterministic fake encoder and a disposable SQLite database, do not download a model, and do not touch the governed database. A separate explicitly invoked integration test uses only an already-downloaded local model.
10. Record actual model disk footprint, load time, peak RSS, and representative CPU inference latency in the implementation verification report; label all estimates as estimates.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| A local inference library or model loader attempts Hub access | Use a configured local path, pinned revision during setup, `local_files_only=True`, and an offline integration test with network blocked. |
| Model absence blocks retrieval or silently changes behavior | Do not load at startup; report an explicit unavailable state and preserve clearly labeled TF-IDF/BM25 fallback. |
| Stale vectors survive text/model changes | Store text hash, model revision, and dimension; revalidate before reuse and update/delete embeddings transactionally. |
| Cross-student or cross-course leakage through vector ranking | Enforce user/course predicates in candidate SQL before vector reads and similarity scoring; test that unauthorized rows are never candidates. |
| Inconsistent vector encoding or score thresholds | Version the serialization and model; normalize embeddings consistently; configure and test thresholds on labeled local examples. |
| CPU latency or memory exceeds expectations | Measure the actual target machine before release; compare L3 if L6 misses agreed operational criteria. Do not claim performance based on unmeasured estimates. |
| Overstated semantic quality | Require the real-model different-vocabulary test and representative human-reviewed course examples. Similarity scores are retrieval ranks, not probabilities or plagiarism findings. |
| License or model revision changes | Pin an immutable revision and preserve its license metadata/text with the model distribution. |
| Governed academic data is changed during testing | Use the existing temporary test database setup, verify `DATABASE_PATH` in test subprocesses, and never initialize or migrate `app/data/governed_academic.db`. |

## Phase 1 verification record

- Read-only inspection covered the Lab 4 stores, routes, models, explicit database schema, BM25 knowledge service/store, related tests, dependencies, and relevant README/architecture/compliance documentation.
- Environment inspection: Python 3.12.10; Windows 11; Intel Core i5-12450H, 8 cores / 12 logical processors; 16,891,633,664 bytes physical RAM; NumPy 2.5.4; Sentence Transformers, Transformers, PyTorch, and ONNX Runtime not installed.
- Candidate parameter, dimension, weight-size, revision, and license claims are from the cited Hugging Face APIs/model cards below. CPU latency, peak model-process RAM, CourseAgentAI retrieval quality, local loading, and offline behavior are **not measured**.
- No tests were run in this evaluation-only phase. The existing tests were inspected but are not evidence of embedding behavior.
- No model was downloaded; no package was installed; no source, dependency manifest, database, or governed record was modified.

## Sources

Primary project evidence:

- `app/labs/lab4/knowledge_store.py`
- `app/labs/lab4/session_store.py`
- `app/api/routes_lab4.py`
- `app/models/lab4_models.py`
- `app/data/db.py`
- `app/knowledge/store.py`
- `app/knowledge/service.py`
- `tests/test_lab4_memory.py`
- `tests/test_lab4_api.py`
- `tests/conftest.py`
- `requirements.txt`
- `README.md`
- `ARCHITECTURE.md`
- `OFFICIAL_14_LAB_COMPLIANCE_AUDIT.md`

External model/runtime evidence:

- [all-MiniLM-L6-v2 model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [all-MiniLM-L6-v2 encoder configuration](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/raw/main/config.json)
- [all-MiniLM-L6-v2 repository metadata and file sizes](https://huggingface.co/api/models/sentence-transformers/all-MiniLM-L6-v2/tree/main?recursive=false)
- [all-MiniLM-L6-v2 model metadata and revision](https://huggingface.co/api/models/sentence-transformers/all-MiniLM-L6-v2)
- [paraphrase-MiniLM-L3-v2 model card](https://huggingface.co/sentence-transformers/paraphrase-MiniLM-L3-v2)
- [paraphrase-MiniLM-L3-v2 encoder configuration](https://huggingface.co/sentence-transformers/paraphrase-MiniLM-L3-v2/raw/main/config.json)
- [paraphrase-MiniLM-L3-v2 repository metadata and file sizes](https://huggingface.co/api/models/sentence-transformers/paraphrase-MiniLM-L3-v2/tree/main?recursive=false)
- [paraphrase-MiniLM-L3-v2 model metadata and revision](https://huggingface.co/api/models/sentence-transformers/paraphrase-MiniLM-L3-v2)
- [SentenceTransformer API: local paths, CPU, revision, local-only loading, and remote-code control](https://sbert.net/docs/package_reference/sentence_transformer/model.html)
- [Hugging Face Transformers installation and offline mode](https://huggingface.co/docs/transformers/installation#offline-mode)
- [Sentence Transformers PyPI metadata](https://pypi.org/project/sentence-transformers/)
- [Sentence Transformers semantic similarity documentation](https://sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html)

## Phase 2 implementation and verification

The approved primary candidate, `sentence-transformers/all-MiniLM-L6-v2`, passed the required evaluation and was integrated. It was pinned to revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. Since the primary passed the resource and compatibility checks, `paraphrase-MiniLM-L3-v2` was not installed or evaluated.

### Environment and measured footprint

- Python 3.12.10, Windows 11, Intel Core i5-12450H (8 cores / 12 logical processors), CPU-only.
- PyTorch `2.8.0+cpu`, Sentence Transformers `5.2.3`, Transformers `5.23.0`, Hugging Face Hub `2.4.0`; `pip check` reported no broken requirements.
- Model directory: **91,587,680 bytes** across 28 files; `model.safetensors`: **90,868,376 bytes**.
- Model load: **0.533 seconds** after runtime imports.
- Warmed single-query inference over 20 iterations: **11.881 ms median**, **13.064 ms p95**.
- Peak process working set: **492,355,584 bytes** (~469.5 MiB).

These are measurements from this machine, not portable service-level guarantees.

### Semantic comparison and offline verification

The query “How can the agent learn from consequences and make better decisions in later steps?” was compared with a conceptually related autonomous-agent passage and an unrelated water-cycle passage:

| Method | Related passage | Unrelated passage | Ranking |
|---|---:|---:|---|
| Local L6 normalized-vector cosine | 0.383822 | 0.088424 | Related first |
| Existing lexical TF-IDF cosine | 0.046584 | 0.060723 | Unrelated first |

This controlled pair demonstrates the expected semantic-vs-lexical distinction for one example only; it is not a broad quality benchmark. Offline inference passed with `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and socket connections blocked.

### Implemented behavior

- `LocalEmbeddingService` lazily loads the pinned model from the configured local directory, CPU-only, with `local_files_only=True` and `trust_remote_code=False`. Normal startup does not load or download the model.
- `scripts/download_lab4_embedding_model.py` explicitly downloads the pinned revision and writes a local manifest. `scripts/index_lab4_embeddings.py` explicitly rebuilds vectors and checks the resolved path and same-file identity against the governed database before initialization. The exact governed-path refusal was exercised and exited with code 2.
- `lab4_memory_embeddings` and `lab4_submission_embeddings` persist float32 vectors, text hashes, model/revision/dimension, owner/course scope, and timestamps, with source foreign keys and cascading deletion. Text/model changes invalidate the old vector and regenerate on the next semantic query or explicit batch rebuild.
- Semantic candidates are filtered in SQL by authenticated owner/course before vector encoding and ranking. Submission vectors contain assignment ID/title, repository name, and student notes only; repository content is neither fetched nor analyzed.
- Existing lexical TF-IDF remains the default. Semantic retrieval is explicit, and missing/corrupt local models result in an explicitly labeled lexical fallback with a reason. Course-document retrieval and citations remain the existing BM25 system; there is no semantic course-material index or hybrid ranking.

### Tests and safety checks

- Targeted real-model tests: **33 passed in 24.63 seconds**, including `test_real_local_model_semantic_ranking_cpu_and_offline`.
- Full suite with `LAB4_RUN_MODEL_INTEGRATION_TESTS=1`: **312 passed, 1 warning in 78.28 seconds**.
- `python -m compileall -q app tests scripts`: passed.
- `node --check app\static\app.js`: passed.
- `python -m pip check`: no broken requirements.
- The embedding indexer was invoked with `app\data\governed_academic.db` and refused before database initialization (exit code 2).
- The governed DB and preserved backup each remained **405,504 bytes** with SHA-256 `A6D98C12D50B96F4996C4016953239A368D7683A7613815E2BA337B322B67AEC`.

The only full-suite warning is pytest-asyncio's notice that the default fixture event-loop scope will change in a future release. Tests use disposable databases via `tests/conftest.py`. One initial full-suite collection attempt failed because `pypdf` was absent from the base dependency manifest; `pypdf>=4.0.0` was added for the application's existing PDF extraction support, and the complete suite passed afterward.

**Result:** The real-model, offline, scoped memory/submission-metadata semantic retrieval gap is implemented and verified. This does not complete all Course Project worklet integration requirements, establish broad retrieval quality, index course documents semantically, or analyze submission repository contents.
