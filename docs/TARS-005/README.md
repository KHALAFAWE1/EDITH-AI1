# TARS-005: Multilingual Semantic Retrieval Architecture & Verification Documentation
## Project Overview & Archive Index

---

### 1. Executive Summary & Mission
**TARS-005** is the engineering initiative to resolve cross-lingual semantic retrieval failures identified in the **TARS-004** Generalization and Reliability Acceptance Test for the TARS AI platform (`EDITH-AI`).

* **Target Capability:** Seamless cross-language semantic retrieval (Arabic $\leftrightarrow$ English) while preserving exact lexical retrieval, structured metadata re-ranking (TARS-003), memory provenance, verification integrity, and local host performance.
* **Target Environment:** Windows 10 AMD64, Intel Core i5-4200M (Haswell 2-core / 4-thread @ 2.50 GHz, AVX2 supported), 7.92 GB RAM, CPU-only execution.
* **Current Operational Baseline:** SQLite database with verified episodic memories, FastAPI/Uvicorn backend service, commit `42f3d5b`.

---

## 2. Chronological Phase Index

| Phase Code | Document Name | Technical Focus & Scope | Execution Status |
|:---:|---|---|:---:|
| **Phase 1** | [`PHASE-01-ARCHITECTURE-REVIEW.md`](./PHASE-01-ARCHITECTURE-REVIEW.md) | Retrieval Architecture, Dual Embeddings, Score Decoupling, Wilson / Clopper-Pearson Sample Sizes | **Review Completed (Read-Only)** |
| **Phase 2.1** | [`PHASE-02.1-ENVIRONMENT-AUDIT.md`](./PHASE-02.1-ENVIRONMENT-AUDIT.md) | Host Hardware, Python 3.14.6, ONNX Runtime 1.28.0, RAM/Disk Availability Audit | **Completed (Read-Only)** |
| **Phase 2.2** | [`PHASE-02.2-MODEL-SOURCE-VERIFICATION.md`](./PHASE-02.2-MODEL-SOURCE-VERIFICATION.md) | Hugging Face Repository Audit, Commit Reconciliation, Missing `vocab.txt` Discovery | **Completed (Read-Only)** |
| **Phase 2.2.1** | [`PHASE-02.2.1-TOKENIZER-STRATEGY.md`](./PHASE-02.2.1-TOKENIZER-STRATEGY.md) | Tokenizer Strategy, XLM-RoBERTa Contract, Python 3.14 Wheel Compatibility | **Completed (Architecture Approved)** |
| **Phase 2.2.2** | [`PHASE-02.2.2-RAM-SAFETY-REVIEW.md`](./PHASE-02.2.2-RAM-SAFETY-REVIEW.md) | Dynamic 3-Tier RAM Safety Architecture, Fallback Policy, Benchmark Methodology | **Completed (Read-Only)** |
| **Phase 2.3** | [`PHASE-02.3-ARTIFACT-INTEGRITY.md`](./PHASE-02.3-ARTIFACT-INTEGRITY.md) | Isolated Download & SHA-256 Checksum Verification of ONNX INT8 and Tokenizer Assets | **Completed (Zero Inference)** |
| **Phase 2.4-A** | [`PHASE-02.4-A-TOKENIZERS-INSTALLATION.md`](./PHASE-02.4-A-TOKENIZERS-INSTALLATION.md) | Isolated Installation of `tokenizers==0.23.3` with `--no-deps` on Python 3.14 | **Completed** |
| **Phase 2.4-B** | [`PHASE-02.4-B-TOKENIZER-ROUNDTRIP.md`](./PHASE-02.4-B-TOKENIZER-ROUNDTRIP.md) | Special Token IDs (`<s>`=0, `<pad>`=1, `</s>`=2, `<unk>`=3) & Roundtrip Verification | **Completed (Zero Inference)** |
| **Phase 2.4-C** | [`PHASE-02.4-C-UNICODE-EDGE-CASES.md`](./PHASE-02.4-C-UNICODE-EDGE-CASES.md) | Tokenizer Edge-Case Audit & Behavior Specification (Emoji, Whitespace, ZWJ/ZWNJ, Arabic Diacritics) | **Completed (Zero Inference)** |

---

## 3. Core Architectural Decisions Summary

1. **Model Selection & Immutable Revision:**
   * Model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
   * Commit SHA: `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`
   * Approved Artifact: `onnx/model_quint8_avx2.onnx` (118.5 MB, AVX2-quantized for Intel Haswell i5-4200M).
   * License: Apache 2.0.
2. **Tokenizer Implementation:**
   * Package: `tokenizers==0.23.3` (Hugging Face Rust-based fast tokenizer).
   * Wheel: `tokenizers-0.23.3-cp310-abi3-win_amd64.whl` (CPython Stable ABI, zero compiler needed).
   * Asset: `tokenizer.json` (250,002 Unigram vocabulary, Metaspace pre-tokenization, Template post-processing).
3. **Database & Storage Isolation:**
   * Canonical Cache: `server/models/cache_tars005/`.
   * Dual Embedding Storage: Dedicated table `tars_memory_embeddings` (keyed by `memory_id` and `model_version`) preserving legacy 128-D vectors in `tars_memories`.
   * Enforced `PRAGMA foreign_keys = ON;` and `content_hash` idempotency.
4. **Three-Tier RAM Safety Gate:**
   * Loading Gate: Dynamic headroom check before session initialization.
   * Inference Gate: Per-query memory guard.
   * Runtime Watchdog: Process RSS drift and leak detection across repeated queries.
   * Safe Fallback: Transparent automatic degradation to TARS-003 lexical search if memory conditions fail.

---

## 4. Pending & Deferred Tests (Roadmap to Phase 3 & 4)

The following tests remain deferred and will be executed under explicit authorization:

* **Phase 2.5 — Host Baseline Benchmark:**
  * 200 warm inference iterations on Intel i5-4200M CPU.
  * Measurement of cold load latency, P50, P90, P95, P99 latency, RAM RSS delta, and CPU thermal throttling.
* **Phase 2.6 — Quantization Drift Test:**
  * Cosine similarity verification between FP32 and INT8 embeddings across 100 benchmark sentences ($\text{Cosine} \ge 0.992$).
* **Phase 4 — Independent Channel Calibration ($\mathcal{D}_{\text{calib}}$):**
  * Sweep candidate generation thresholds ($\theta_{\text{lex\_cand}}$, $\theta_{\text{multi\_cand}}$).
  * Calibrate Semantic Floor ($\theta_{\text{floor}}$) and Acceptance Gate ($\theta_{\text{accept}}$).
* **Phase 4 — Held-Out Blind Evaluation ($\mathcal{D}_{\text{eval}}$):**
  * Statistically rigorous unknown query rejection test ($N \ge 300$) to prove $\text{FPR} \le 1\%$ at 95% confidence.
  * Held-out cross-lingual retrieval battery (Arabic $\leftrightarrow$ English).
  * Concurrent API load degradation test (5 concurrent clients during active embedding).

---

## 5. Technical Artifacts Archive

Supporting data and verification manifests are preserved in:
* [`docs/TARS-005/artifacts/model_verification_manifest.json`](./artifacts/model_verification_manifest.json): Checksums and metadata for acquired model assets.
* [`docs/TARS-005/artifacts/tokenizer_edge_case_results.json`](./artifacts/tokenizer_edge_case_results.json): Full character-level codepoint mappings and edge-case test results.
* [`docs/TARS-005/artifacts/tokenizer_verification_results.json`](./artifacts/tokenizer_verification_results.json): Initial roundtrip test data.
