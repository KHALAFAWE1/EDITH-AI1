# TARS-005 — Phase 2.2.2: RAM Safety Gate & Execution Readiness
## Memory Safety Policy & Benchmark Methodology Report

* **Phase Code:** Phase 2.2.2
* **Execution Date:** 2026-11-06
* **Document Status:** `Completed (Read-Only Review)`
* **Operational Scope:** Critical engineering analysis of host memory dynamics on Windows 10, multi-tier safety gate architecture, safe fallback mechanisms, and empirical benchmark protocols.

---

## 1. Why a Static 300 MB Threshold is Insufficient

Empirical monitoring of the host machine revealed that a fixed static threshold (such as 300 MB) does not guarantee memory safety:
* **Host Memory Volatility:** During testing, available RAM on the target host fluctuated from **$440\text{ MB}$ ($94.5\%$ used)** during external task activity to **$1,981\text{ MB}$ ($75.5\%$ used)** when idle.
* **Windows Standby List:** `Available RAM` in Windows includes Standby Cache. Under rapid allocation spikes, reclaiming standby pages incurs heavy disk I/O and pagefile swapping, inducing latency spikes.
* **Session Initialization Spikes:** Memory allocators (mimalloc / CRT) allocate temporary workspace buffers and memory-mapped graphs during ONNX session creation, producing peak allocations $2\times - 3\times$ the file size.
* **Uvicorn Baseline Footprint:** The live Uvicorn/FastAPI process operates with a steady-state working set of $341.6\text{ MB}$ RSS. Concurrent requests during model initialization can rapidly exhaust unreserved headroom.

---

## 2. Three-Tier Memory Safety Architecture

```
[ Tier 1: Model-Loading Gate ] ──> Checks physical available RAM and commit charge before session init.
                                   If failed: Disable multilingual model, route to lexical engine.

[ Tier 2: Inference-Time Gate ] ──> Per-query lightweight check (< 0.1 ms).
                                   If failed: Return lexical retrieval with fallback metadata warning.

[ Tier 3: Runtime Watchdog ]   ──> Periodic check across repeated queries (every N queries).
                                   Detects RSS working set creep, memory leaks, and host memory pressure.
```

---

## 3. Memory Component Measurement Breakdown

To avoid theoretical assumptions, runtime memory must be profiled across six distinct components:
1. **ONNX Runtime Session Init:** C++ heap allocation, operator kernels, thread pools (`intra_op_num_threads = 2`).
2. **Quantized Model Weights:** Deserialized AVX2 quantized matrices ($118.5\text{ MB}$ on disk, $\approx 140\text{ MB}$ memory footprint).
3. **Tokenizer Trie Heap:** Rust heap memory for 250,002 vocabulary tokens and precompiled normalizer tables ($\approx 15\text{ MB}$).
4. **Input Tensors:** Integer buffers (`input_ids` and `attention_mask` `[1, seq_len]` int64).
5. **Output Tensors:** Float32 buffer for `last_hidden_state` `[1, seq_len, 384]`.
6. **Mean Pooling Workspace:** NumPy temporary intermediate arrays during mask expansion, summation, and $L_2$ normalization.

---

## 4. Safe Rejection & Fallback Protocol

* **Zero Crash Policy:** A failure in any memory gate must **never** raise unhandled exceptions or crash the Uvicorn server.
* **Graceful Degradation:** The request seamlessly falls back to the TARS-003 structured lexical retrieval engine.
* **Transparent Metadata:** The response metadata explicitly flags degradation:
  `"retrieval_mode": "lexical_fallback", "degradation_reason": "host_memory_pressure_guard"`

---

## 5. Explicit File Size vs. Memory Reality Confirmation

> [!CAUTION]
> **Architectural Prohibition:**
> The system must **never** assume a model is safe to load merely because its ONNX file on disk is relatively small ($118.5\text{ MB}$). Actual execution safety is determined by peak runtime working set, allocator buffer pools, and host memory pressure, verified exclusively through empirical benchmarking.
