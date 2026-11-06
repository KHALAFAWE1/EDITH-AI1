# TARS-005 — Phase 2.4-C: Tokenizer Edge-Case Audit & Unicode Behavior
## Detailed Edge-Case Audit & Character-Level Investigation Report

* **Phase Code:** Phase 2.4-C
* **Execution Date:** 2026-11-06
* **Document Status:** `Completed (Zero Inference Executed)`
* **Methodological Classification:** **Internal Tokenizer Behavior Specification** (Evaluated without external PyTorch/Transformers runtime).
* **Raw Artifact Location:** [`scratch/tokenizer_edge_case_results.json`](./artifacts/tokenizer_edge_case_results.json)

---

## 1. Emoji Discrepancy Root-Cause Analysis

### Test Case: `TARS AI System 🛰️🚀`
* **Input Characters & Codepoints:**
  * ASCII text: `TARS AI System `
  * Satellite Emoji: **`🛰` (U+1F6F0)**
  * Variation Selector-16: **`️` (U+FE0F)**
  * Rocket Emoji: **`🚀` (U+1F680)**

### Sub-Token Level Mapping & Codepoints:
```text
Index 0 -> Token '<s>'     (ID:      0) [U+003C, U+0073, U+003E]
Index 1 -> Token '▁TAR'    (ID:  55734) [U+2581, U+0054, U+0041, U+0052]
Index 2 -> Token 'S'       (ID:    294) [U+0053]
Index 3 -> Token '▁AI'     (ID:  38730) [U+2581, U+0041, U+0049]
Index 4 -> Token '▁System' (ID:  12353) [U+2581, U+0053, U+0079, ...]
Index 5 -> Token '▁'       (ID:      6) [U+2581]
Index 6 -> Token '<unk>'   (ID:      3) [U+1F6F0 ('🛰')]  <-- OUT-OF-VOCABULARY
Index 7 -> Token '️'       (ID:  15755) [U+FE0F]        <-- IN-VOCABULARY
Index 8 -> Token '🚀'      (ID: 247206) [U+1F680]        <-- IN-VOCABULARY
Index 9 -> Token '</s>'    (ID:      2) [U+003C, U+002F, ...]
```

### Empirical Root Cause:
* **Raw Decode (`skip_special_tokens=False`):**
  Output: `<s> TARS AI System <unk>️🚀</s>` (The `<unk>` token is explicitly preserved).
* **Clean Decode (`skip_special_tokens=True`):**
  Output: `TARS AI System ️🚀`
* **Mathematical Cause:**
  1. Satellite emoji `🛰` (U+1F6F0) is not in the model's 250,002 vocabulary and maps to `<unk>` (ID: 3).
  2. `skip_special_tokens=True` elides `<unk>` because it is defined as a special token.
  3. The transparent Variation Selector `\uFE0F` (ID: 15755) and Rocket emoji `🚀` (ID: 247206) are standard vocabulary tokens and remain in the decoded string.
  4. This accounts for the observed character difference ($23 \rightarrow 22$ characters).

---

## 2. Whitespace Normalization Behavior

The SentencePiece Metaspace pre-tokenizer enforces canonical whitespace handling:

| Whitespace Pattern | Input Example | Decoded Clean Output | Architectural Behavior |
|---|---|---|---|
| **Multiple Spaces** | `'TARS    AI    Core'` | `'TARS AI Core'` | Collapses multiple spaces into single space |
| **Leading & Trailing** | `'   TARS AI   '` | `'TARS AI'` | Trims leading and trailing whitespace |
| **Tabs** | `'TARS\tAI\tCore'` | `'TARS AI Core'` | Normalizes tab to single space |
| **Newlines / CRLF** | `'TARS\r\nAI\nCore'` | `'TARS AI Core'` | Normalizes newlines to single space |
| **Mixed Clusters** | `'  \t\n TARS \r\n AI \t '` | `'TARS AI'` | Cleans and normalizes word boundaries |

* **Retrieval Impact:** Beneficial for search retrieval, as query variations caused by extra spaces or newline formatting map to identical token sequences.

---

## 3. Standardized Token-Count Reporting Convention

All subsequent benchmark and retrieval modules must adhere to this standardized reporting schema:
* **Total Token IDs ($N_{\text{total}}$):** `len(encoding.ids)` (Includes `<s>` prefix and `</s>` suffix).
* **Content Token IDs ($N_{\text{content}}$):** `len(encoding.ids) - 2` (Excludes template wrappers).
* **Special Token Count ($N_{\text{special}}$):** Exactly 2 for single-sentence inputs (Index 0 is `<s>`, Index $-1$ is `</s>`).
* **Attention Mask Length:** Exactly equal to $N_{\text{total}}$ (`len(encoding.attention_mask)`).

---

## 4. Advanced Unicode Edge Cases Matrix

| Edge Case Domain | Input Text | Token Counts ($N_{\text{total}} / N_{\text{content}}$) | Decoded Clean Output | Status | Detailed Mechanism |
|---|---|:---:|---|:---:|---|
| **Arabic Diacritics** | `"سَيَّارَةٌ جَدِيدَةٌ"` | 18 / 16 | `"سَيَّارَةٌ جَدِيدَةٌ"` | **PASS** | 100% exact match; Harakat preserved as distinct tokens |
| **Arabic Sukun & Tanween** | `"مَكْتَبًا وَمَدْرَسَةٍ"` | 23 / 21 | `"مَكْتَبًا وَمَدْرَسَةٍ"` | **PASS** | 100% exact match |
| **Standard Arabic Lam-Alif** | `"لا لأ لإ"` | 5 / 3 | `"لا لأ لإ"` | **PASS** | Standard characters preserved |
| **Arabic Presentation Forms-B** | `"\uFEFB\uFEFC\uFEF7"` (`ﻻﻼﻷ`) | 5 / 3 | `"لالالأ"` | **PASS** | NFKC automatically decomposes ligatures to standard letters |
| **Combining Accents (NFD)** | `"e\u0301cole"` | 4 / 2 | `"école"` | **PASS** | Decomposed `e` + `\u0301` normalized to precomposed `é` |
| **Precomposed Accents (NFC)** | `"école"` | 4 / 2 | `"école"` | **PASS** | 100% exact match |
| **Emoji with Selector-16** | `"✈️ vs ✈"` | 8 / 6 | `"✈️ vs ✈"` | **PASS** | Correctly differentiates presentation styles |
| **Zero-Width Joiner (ZWJ)** | `"مـ\u200Dـتـ\u200Dـصـ\u200Dـل"` | 12 / 10 | `"مـ ـتـ ـصـ ـل"` | **PASS** | Metaspace treats ZWJ controls as subword splits |
| **Zero-Width Non-Joiner (ZWNJ)**| `"می\u200Cخواهم"` | 4 / 2 | `"می خواهم"` | **PASS** | ZWNJ treated as canonical word boundary |

---

## 5. Execution Boundary Confirmation

* Zero ONNX model weights loaded into memory.
* Zero ONNX Runtime InferenceSessions created.
* Zero vector embeddings generated.
* Production code, APIs, database, and UI remained completely untouched.
