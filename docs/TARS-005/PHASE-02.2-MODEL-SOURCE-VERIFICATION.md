# TARS-005 — Phase 2.2: Model Source & Artifact Verification
## Read-Only Model Source Verification Report

* **Phase Code:** Phase 2.2
* **Execution Date:** 2026-11-06
* **Document Status:** `Completed (Read-Only)`
* **Candidate Model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
* **Operational Scope:** Remote API inspection of official Hugging Face repository metadata, commit history, and artifact trees without downloading model weights.

---

## 1. Verified Official Facts

1. **Repository Identity & Official Licensing:**
   * Official Repository: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
   * Official License: **`Apache License 2.0`** (Verified via repository metadata tag: `license: apache-2.0`).
2. **Model Vector Specifications:**
   * Dense Vector Dimensionality: **384 dimensions** (`word_embedding_dimension: 384`).
   * Architecture: BertModel (`BertModel` in `config.json`, 12 hidden layers, 384 hidden size).
   * Pooling Strategy: `1_Pooling/config.json` specifies:
     * `pooling_mode_mean_tokens: True` (Mean pooling over token embeddings where `attention_mask == 1`).
     * `pooling_mode_cls_token: False`.
     * `pooling_mode_max_tokens: False`.
   * Normalization: Post-pooling Euclidean $L_2$ vector normalization ($\|\mathbf{v}\|_2 = 1.0$).
3. **ONNX Graph Contract:**
   * **Input Tensors:** `input_ids` (int64 `[batch, seq_len]`), `attention_mask` (int64 `[batch, seq_len]`).
   * **Output Tensors:** `last_hidden_state` (float32 `[batch, seq_len, 384]`).
   * **Text Preprocessing:** The ONNX graph does **not** include text tokenization; integer token IDs must be supplied by the host tokenizer.

---

## 2. Discrepancies & Critical Architecture Findings

### 2.1 Invalid Commit Hash Reconciliation
* **Finding:** The commit hash proposed in early briefs (`bf3bf13ab40ac8715bf94851ab523f2621ad7064`) returned **HTTP 404 Not Found** on the official Hugging Face API.
* **Historical Commit:** Inspection of the Git commit tree revealed the closest matching historical commit was `bf3bf13ab40c3157080a7ab344c831b9ad18b5eb` (March 27, 2024).
* **CRITICAL FINDING:** At commit `bf3bf13ab40c3157...`, the `onnx/` directory **did not exist in the repository**. Only PyTorch, Safetensors, and TensorFlow weights existed.
* **Resolution:** The canonical commit containing verified ONNX exports was identified as:
  **`e8f8c211226b894fcb81acc59f3b34ba3efd5f42`**

### 2.2 The Missing `vocab.txt` & Tokenizer Reality
* **Preliminary Assumption:** Preliminary designs assumed a BERT-style WordPiece tokenizer using `vocab.txt`.
* **Empirical Reality:** File `vocab.txt` **does not exist across any revision of this repository**.
* **Model Tokenizer Type:** `paraphrase-multilingual-MiniLM-L12-v2` is an XLM-RoBERTa / SentencePiece Unigram architecture with a vocabulary of 250,002 tokens.
* **Actual Tokenizer Assets:**
  * `tokenizer.json` (Hugging Face Fast Tokenizer JSON, 9,081,518 bytes).
  * `sentencepiece.bpe.model` (Binary SentencePiece model, 5,069,051 bytes).
  * `unigram.json` (Unigram model, 14,763,234 bytes).
* **Consequence:** A custom "pure-Python WordPiece tokenizer from `vocab.txt`" is physically impossible with this model.

---

## 3. Discovered ONNX Artifacts at Canonical Commit `e8f8c21`

| Repository File Path | Size (Bytes) | Format & Target Instruction Set | Suitability for Intel i5-4200M |
|---|:---:|---|---|
| `onnx/model.onnx` | $470,301,610$ | ONNX FP32 Baseline | Unsuitable (Excessive RAM footprint) |
| `onnx/model_quint8_avx2.onnx` | **$118,453,870$** | **ONNX uint8 Quantized (AVX2 Tuned)** | **Optimal Match (Hardware AVX2 Supported)** |
| `onnx/model_qint8_avx512.onnx` | $118,412,398$ | ONNX int8 Quantized (AVX-512) | Incompatible (i5-4200M lacks AVX-512) |
| `tokenizer.json` | $9,081,518$ | Tokenizers JSON Format | Required Tokenizer Definition |
| `config.json` | $645$ | JSON Architecture Config | Required Model Config |

---

## 4. Official Source References

* **Model Repository Metadata:** `https://huggingface.co/api/models/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
* **Canonical Tree at Commit `e8f8c21`:** `https://huggingface.co/api/models/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/tree/e8f8c211226b894fcb81acc59f3b34ba3efd5f42`
* **Mean Pooling Config:** `https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/raw/e8f8c211226b894fcb81acc59f3b34ba3efd5f42/1_Pooling/config.json`
