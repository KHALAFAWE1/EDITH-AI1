# TARS-005 — Phase 1: Architecture Review & Retrieval Design
## Engineering Specification & Final Architectural Review

* **Phase Code:** Phase 1
* **Document Status:** `Architecture Review Completed (Read-Only)`
* **Operational Scope:** Read-only architectural design and statistical calibration specification. Zero production code, databases, or model files modified.
* **Baseline Git Commit:** `42f3d5b` (`test(acceptance): TARS-004 Generalization and Reliability Acceptance Test`)

---

## 1. Problem Statement & Evidence from TARS-004

In the TARS-004 Generalization and Reliability Acceptance Test, the retrieval subsystem achieved:
* Arabic intra-language retrieval: **100.0%** ($5/5$)
* English intra-language retrieval: **92.3%** ($12/13$)
* Exact query retrieval: **100.0%** ($3/3$)
* Disambiguation of sibling components: **100.0%** ($4/4$)
* Cross-lingual semantic retrieval: **0.0%** ($0/2$)
  * Query (Arabic): `"ما هو خادم الذاكرة المؤقتة السريع المستخدم في البنية التحتية؟"` $\rightarrow$ Expected English memory: Redis memory record. Result: Unranked / Not found.
  * Query (English): `"What is the surface gravity of Mars?"` $\rightarrow$ Expected Arabic memory: Mars gravity record. Result: Unranked / Not found.

**Root Cause:**
The existing retrieval engine relies on character n-grams, BM25 token overlap, and a 128-D random-projection embedding in `tars_core.py`. These lexical techniques cannot bridge the semantic gap between non-cognate natural languages where vocabulary and character distributions share zero overlap.

---

## 2. Statistical Validity & Calibration Specification

### 2.1 The Mathematical Impossibility of $N=20$ for $\text{FPR} \le 1\%$
A preliminary design draft suggested using $N=20$ unknown samples to verify a False Positive Rate ($\text{FPR}$) $\le 1.0\%$. Under rigorous statistical theory, this claim is mathematically invalid:

1. **Clopper-Pearson One-Sided Exact Binomial Interval ($95\%$ Confidence):**
   When zero false positives ($k = 0$) are observed across $N$ trials, the true false positive probability $p$ satisfies:
   $$(1 - p)^N \le \alpha \implies N \ge \frac{\ln(\alpha)}{\ln(1 - p)}$$
   For $\alpha = 0.05$ (95% confidence) and target $p \le 0.01$ (1% FPR):
   $$N \ge \frac{\ln(0.05)}{\ln(0.99)} \approx \frac{-2.99573}{-0.01005} \approx 298.07 \implies \mathbf{N \ge 299}$$
   *(The classical Rule of Three approximation $3/N \le 0.01 \implies N \ge 300$ derives directly from this formula).*

2. **Wilson Score Two-Sided Interval ($95\%$ Confidence, $z = 1.96$):**
   $$p_U = \frac{z^2}{N + z^2} = \frac{1.96^2}{N + 1.96^2} = \frac{3.8416}{N + 3.8416} \le 0.01 \implies \mathbf{N \ge 381}$$

3. **Wilson Score One-Sided Interval ($95\%$ Confidence, $z = 1.645$):**
   $$p_U = \frac{1.645^2}{N + 1.645^2} = \frac{2.706}{N + 2.706} \le 0.01 \implies \mathbf{N \ge 268}$$

**Architectural Requirement:**
To statistically substantiate an $\text{FPR} \le 1.0\%$ at 95% confidence, the unknown query evaluation set must contain **at least $N = 300$ held-out unknown queries** with zero false acceptances observed.

### 2.2 Dataset Partitioning: Calibration vs. Held-Out Evaluation
* **Calibration Dataset ($\mathcal{D}_{\text{calib}}$, $N = 350$ queries):**
  * 100 In-Domain Known Positives
  * 100 Hard-Negative Sibling Queries
  * 150 Out-of-Domain Unknown Queries
  * *Purpose:* Threshold sweeping, ROC/PR curve generation, and operational cutoff selection.
* **Held-Out Evaluation Dataset ($\mathcal{D}_{\text{eval}}$, $N = 350$ queries):**
  * 100 In-Domain Known Positives
  * 100 Hard-Negative Sibling Queries
  * 150 Out-of-Domain Unknown Queries
  * *Purpose:* Blind, zero-tuning acceptance evaluation with exact Wilson 95% confidence intervals.

---

## 3. Score Semantics, Fusion & Evidence Decoupling

### 3.1 Score Incompatibility
Raw scores from distinct retrieval spaces cannot be tested against a shared scalar threshold:
* **Lexical Similarity ($S_{\text{lex}} \in [0.0, 1.0]$):** Token and character n-gram overlap.
* **Multilingual Semantic Cosine ($S_{\text{multi}} \in [-1.0, 1.0]$):** Dot product of $L_2$-normalized dense embeddings.
* **Reciprocal Rank Fusion Score ($S_{\text{RRF}}(d) \in [0.0, 0.033]$):**
  $$S_{\text{RRF}}(d) = \sum_{m \in \{\text{lex}, \text{multi}\}} \frac{w_m}{k + r_m(d)}, \quad k = 60$$

### 3.2 Dual-Gate Evidence Policy (Preventing Metadata Leakage)
A critical flaw in preliminary designs allowed structured metadata bonuses ($\Delta_{\text{subject}} = +0.25$, $\Delta_{\text{subsystem}} = +0.15$) to resurrect irrelevant text matches ($S \approx 0.35$) past the acceptance gate. The approved architecture decouples relevance from re-ranking:

1. **Gate 1 — Semantic Relevance Floor:**
   $$\text{Base\_Relevance}(d^*) = \max\left(S_{\text{lex}}(d^*),\; S_{\text{multi}}(d^*)\right) \ge \theta_{\text{floor}} \quad (\text{preliminary prior: } 0.52)$$
   *If the top candidate fails this floor, it is rejected immediately with zero bonus consideration.*
2. **Gate 2 — Bonus-Capped Final Evidence Gate:**
   $$\Delta_{\text{meta}} = \min\left(\Delta_{\text{subject}} + \Delta_{\text{subsystem}} + \Delta_{\text{side}},\; 0.15\right)$$
   $$\text{Final\_Evidence}(d^*) = \text{Base\_Relevance}(d^*) + \Delta_{\text{meta}} - \text{Penalties} \ge \theta_{\text{accept}} \quad (\text{preliminary prior: } 0.62)$$

---

## 4. SQLite Schema & Referential Integrity

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tars_memory_embeddings (
    memory_id TEXT NOT NULL,
    model_version TEXT NOT NULL,
    embedding BLOB NOT NULL,
    dimensions INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (memory_id, model_version),
    FOREIGN KEY (memory_id) REFERENCES tars_memories(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mem_emb_lookup 
ON tars_memory_embeddings(memory_id, model_version);
```

* **Foreign Keys:** Must be enabled on every SQLite connection via connection hook.
* **Transaction Locking:** Must use `BEGIN IMMEDIATE` to prevent `SQLITE_BUSY` deadlocks.
* **Error Logging:** `error_sync_log` must be written outside rolled-back transactions (dedicated log file or isolated connection).

---

## 5. Formal Caveats Recorded

1. Threshold values $\theta_{\text{floor}} = 0.52$ and $\theta_{\text{accept}} = 0.62$ are preliminary design targets, non-operational until calibrated on $\mathcal{D}_{\text{calib}}$.
2. $\max(S_{\text{lex}}, S_{\text{multi}})$ cannot be treated as a unified metric without independent channel calibration.
3. Proving $\text{FPR} \le 1\%$ requires $k=0$ across at least 299 unknown samples (Clopper-Pearson) or 381 samples (Wilson two-sided).
4. Memory and latency estimates remain theoretical until measured on the physical Intel Core i5-4200M host.
5. FP32/INT8 parity and performance under API load are not considered passing until empirical benchmark execution.
