# TARS-005 — Phase 2.4-B: Tokenizer Parity & Roundtrip Verification
## Tokenizer Verification & Internal Roundtrip Report

* **Phase Code:** Phase 2.4-B
* **Execution Date:** 2026-11-06
* **Document Status:** `Completed (Zero Inference Executed)`
* **Active Package:** `tokenizers==0.23.3`
* **Verified Asset:** `server\models\cache_tars005\tokenizer.json`
* **Methodological Classification:** **Internal Roundtrip & Contract Verification** (Classified as internal behavior because no external PyTorch/Transformers runtime was present in the environment).

---

## 1. Tokenizer Structure & Special Token ID Verification

Loaded `tokenizer.json` using `tokenizers.Tokenizer.from_file()`:
* **Total Vocabulary Size:** **250,002 tokens**
* **Model Type:** `Unigram` (SentencePiece Unigram subword distribution)
* **Normalizer:** `Precompiled` (Binary SentencePiece NFKC normalizer)
* **Pre-tokenizer:** `Sequence` (Metaspace with ` ` U+2581 whitespace marker)
* **Decoder:** `Metaspace`

### Special Token ID Verification:
| Token String | Expected ID | Measured Actual ID | Verification Status |
|:---:|:---:|:---:|:---:|
| `<s>` (BOS / CLS) | **0** | **0** | **VERIFIED MATCH** |
| `<pad>` (Padding) | **1** | **1** | **VERIFIED MATCH** |
| `</s>` (EOS / SEP) | **2** | **2** | **VERIFIED MATCH** |
| `<unk>` (Unknown OOV) | **3** | **3** | **VERIFIED MATCH** |
| `<mask>` (Mask) | **250001** | **250001** | **VERIFIED MATCH** |

---

## 2. Encode / Decode Roundtrip Test Matrix

| Test Domain | Input Text | Token Count (Total) | Token IDs Sample | Decoded Output (skip_special=True) | Roundtrip Match |
|---|---|:---:|---|---|:---:|
| **Arabic Script** | `"نظام الملاحة الفضائي وقمر التوجيه"` | 13 | `[0, 9123, 79566, 40586, 359, ...]` | `"نظام الملاحة الفضائي وقمر التوجيه"` | **100% Exact Match** |
| **English Script** | `"Quantum cryptographic key distribution protocol"` | 9 | `[0, 75344, 316, 215637, 48461, ...]` | `"Quantum cryptographic key distribution protocol"` | **100% Exact Match** |
| **Mixed Language** | `"خادم Redis يعمل بسعة 128 ميجابايت على منفذ 6379"` | 17 | `[0, 133470, 6096, 164, 64938, ...]` | `"خادم Redis يعمل بسعة 128 ميجابايت على منفذ 6379"` | **100% Exact Match** |
| **Punctuation & Numbers** | `"2026-11-06T18:50:00Z, [ID #42] -> 99.8% ($100)"` | 25 | `[0, 387, 4046, 36099, 9016, ...]` | `"2026-11-06T18:50:00Z, [ID #42] -> 99.8% ($100)"` | **100% Exact Match** |
| **Arabic Diacritics** | `"العَرَبِيَّةُ مَعَ التَّشْكِيلِ الكَامِلِ"` | 30 | `[0, 5537, 278, 835, 278, 1325, ...]` | `"العَرَبِيَّةُ مَعَ التَّشْكِيلِ الكَامِلِ"` | **100% Exact Match** |
| **Empty Input** | `""` | 2 | `[0, 2]` (`<s>` and `</s>`) | `""` | **Clean Template Packaging** |
| **Whitespace Only** | `"   \t\n  "` | 2 | `[0, 2]` | `""` | **Clean Collapsing** |

---

## 3. Key Behavioral Observations

1. **Automated Template Processing:** `Tokenizer.encode()` automatically injects `<s>` (ID: 0) as prefix and `</s>` (ID: 2) as suffix, satisfying the BertModel / XLM-RoBERTa input requirements.
2. **Arabic Diacritic Preservation:** Harakat (Fatha, Damma, Kasra, Shaddah) are tokenized as distinct subword tokens without being silently stripped, allowing exact roundtrip reconstruction.
3. **Emoji Anomaly Flagged:** Input with satellite emoji (`🛰️`) exhibited a decode length difference, prompting the Phase 2.4-C edge-case investigation.

---

## 4. Execution Boundary Confirmation

* Zero ONNX Runtime InferenceSessions created.
* Zero ONNX model weights loaded into memory.
* Zero inference or embedding vectors generated.
* All test outputs saved in [`scratch/tokenizer_verification_results.json`](./artifacts/tokenizer_verification_results.json).
