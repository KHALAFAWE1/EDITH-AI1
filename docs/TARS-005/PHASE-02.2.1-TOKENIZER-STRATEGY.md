# TARS-005 — Phase 2.2.1: Tokenizer Strategy & Architecture Correction
## Decision Matrix & Architecture Specification Report

* **Phase Code:** Phase 2.2.1
* **Execution Date:** 2026-11-06
* **Document Status:** `Completed (Architecture Approved)`
* **Operational Scope:** Evaluation of tokenizer implementations, PyPI wheel availability on Windows AMD64 Python 3.14, and architectural decisions for model cache and manifest verification.

---

## 1. Technical Decision Matrix

| Evaluation Dimension | Option 1: Hugging Face `tokenizers` (`tokenizer.json`) | Option 2: `sentencepiece` (`sentencepiece.bpe.model`) | Option 3: Isolated Subprocess / Microservice | Option 4: Scratch Pure-Python Tokenizer |
|---|---|---|---|---|
| **Windows AMD64 Support** | **Full** (Verified) | **Full** (Verified) | Supported but complex | Supported |
| **Python 3.14 Wheels** | **Available on PyPI** via `cp310-abi3-win_amd64` (Stable ABI) | **Available on PyPI** via `cp314-cp314-win_amd64` | Requires separate Python runtime | Zero packages needed |
| **Compiler Requirement** | **Zero** (Precompiled binary wheel verified via `--dry-run`) | **Zero** (Precompiled binary wheel verified via `--dry-run`) | Depends on external setup | Zero |
| **Runtime Heap Overhead** | $\approx 15\text{ MB}$ (Rust backend) | $\approx 12\text{ MB}$ (C++ backend) | $\approx 90\text{ MB}$ (Duplicate Python process) | Negligible |
| **CPU Processing Latency** | $< 1\text{ ms}$ per query | $< 1.5\text{ ms}$ per query | $> 10\text{ ms}$ (IPC overhead) | $> 60\text{ ms}$ (Slow 250k parsing) |
| **XLM-RoBERTa Contract** | **Native & Automatic** (`input_ids`, `mask`, template packaging) | **Manual** (Requires Python code for `<s>`, `</s>`, padding) | Native | Highly error-prone |
| **Maintenance Risk** | **Low** (Industry standard) | Moderate | High (Two process lifecycles) | **Critical / Unacceptable** |

---

## 2. XLM-RoBERTa Tokenizer Contract Verification

* **Special Tokens:**
  * `<s>` (Beginning of Sequence / CLS): ID = **`0`**
  * `<pad>` (Padding Token): ID = **`1`**
  * `</s>` (End of Sequence / SEP): ID = **`2`**
  * `<unk>` (Unknown Character Token): ID = **`3`**
  * `<mask>` (Mask Token): ID = **`250001`**
* **Template Processing:**
  Single sentence queries are automatically wrapped as:
  $$[\text{ID: } 0 \ (<s>)] + [\text{Content Token IDs}] + [\text{ID: } 2 \ (</s>)]$$
  With attention mask populated with `1` across all non-padding positions.
* **Pre-tokenization & Normalization:**
  * Normalizer: Precompiled NFKC table.
  * Pre-tokenizer: Metaspace with whitespace replacement symbol ` ` (U+2581). Handles Arabic script, prefixes, and ligatures natively without separate whitespace word splitting.

---

## 3. Approved Architectural Decisions

1. **Commit Hash Confirmation:**
   * Canonical immutable commit confirmed: **`e8f8c211226b894fcb81acc59f3b34ba3efd5f42`**.
2. **Quantized Model Artifact Name:**
   * Canonical artifact confirmed: **`onnx/model_quint8_avx2.onnx`** (118,453,870 bytes).
3. **Tokenizer Implementation Strategy:**
   * Approved: **Option 1 (Hugging Face `tokenizers` package reading `tokenizer.json`)**.
   * Dry-run simulation proved wheel `tokenizers-0.23.3-cp310-abi3-win_amd64.whl` installs without compiling.
4. **Canonical Isolated Cache Location:**
   * Approved: `server\models\cache_tars005\`
5. **Cryptographic Verification Manifest:**
   * Approved: `server\models\cache_tars005\model_verification_manifest.json` recording repository, revision, byte sizes, and pre-computed SHA-256 hashes.
6. **RAM Safety Floor Precondition:**
   * System memory must satisfy dynamic headroom check ($\text{Available RAM} \ge 350\text{ MB}$) before initializing model sessions.
