# TARS-005 — Phase 2.1: Environment & Hardware Audit
## Read-Only Environment & Hardware Verification Report

* **Phase Code:** Phase 2.1
* **Execution Date:** 2026-11-06
* **Document Status:** `Completed (Read-Only)`
* **Operational Scope:** Read-only inspection of host hardware, operating system, Python virtual environment, installed packages, and model cache paths. Zero modifications performed.

---

## 1. Measured Host Environment Baseline

Direct empirical audit performed via `.\venv\Scripts\python.exe` on target host:

| Evaluated Parameter | Measured Value / Status | Verification Method | Evaluation |
|---|---|---|:---:|
| **Target Path** | `C:\Users\Egypt For Computer\Desktop\EDITH-AI` | Project Root Directory | **Verified** |
| **Python Binary** | `Python 3.14.6` | `sys.version` via `.\venv\Scripts\python.exe` | **Active Virtualenv** |
| **ONNX Runtime** | `1.28.0` | `onnxruntime.__version__` | **Installed & Ready** |
| **Execution Providers** | `['AzureExecutionProvider', 'CPUExecutionProvider']` | `ort.get_available_providers()` | **Supported** |
| **CPU Execution Provider** | `CPUExecutionProvider` | Verified present (`True`) | **Mandatory Provider Active** |
| **NumPy Version** | `2.5.1` | `numpy.__version__` | **Installed & Ready** |
| **Operating System** | `Windows 10 Build 10.0.19045` (SP0) | `platform.platform()` | **Supported (AMD64)** |
| **Processor Architecture** | `AMD64` (x86_64) | `platform.machine()` | **64-bit Compatible** |
| **Host CPU Model** | Intel Core (Haswell Family 6 Model 60 Stepping 3) | `platform.processor()` | **AVX2 Supported** |
| **CPU Core Topology** | 2 Physical Cores, 4 Logical Threads @ 2.50 GHz | `psutil.cpu_count(logical=False/True)` | **Thread-Budget Constrained** |
| **Physical System RAM** | Total: $7.92\text{ GB}$ ($8,105.1\text{ MB}$) / Available: **$0.44\text{ GB}$** | `psutil.virtual_memory()` | **Critical ($94.5\%$ used at audit)** |
| **Storage Capacity (C:)** | Total: $97.44\text{ GB}$ / Free: **$31.28\text{ GB}$** | `shutil.disk_usage()` | **Safe & Sufficient** |
| **Model Cache Directory** | `server\models\cache_tars005` | `os.path.exists()` returned `False` | **Uncreated (Read-Only Verified)** |
| **Parent Models Folder** | `server\models` | `os.path.exists()` returned `True`, items: `[]` | **Empty & Clean** |

---

## 2. Target Model File Existence Check (Pre-Acquisition)

Prior to any download authorization, all candidate artifact paths were verified absent:
* `server/models/cache_tars005/model.onnx`: **Absent (`False`)**
* `server/models/cache_tars005/model_quantized.onnx`: **Absent (`False`)**
* `server/models/cache_tars005/tokenizer.json`: **Absent (`False`)**
* `server/models/cache_tars005/vocab.txt`: **Absent (`False`)**
* `server/models/cache_tars005/config.json`: **Absent (`False`)**

---

## 3. Engineering Findings & Constraints

1. **Host RAM Headroom Warning:**
   * At the time of initial audit, available physical RAM was constrained to **$0.44\text{ GB}$ ($440\text{ MB}$)** due to external background host applications.
   * *Architectural Decision:* Loading an unquantized FP32 model ($\approx 470\text{ MB}$ file, $> 500\text{ MB}$ heap footprint) presents extreme risk of host memory exhaustion (OOM crash). Deployment must strictly utilize an AVX2 INT8 quantized artifact ($\approx 118\text{ MB}$) coupled with dynamic memory safety gates.
2. **Zero Missing Core Packages:**
   * `onnxruntime 1.28.0` with `CPUExecutionProvider` and `numpy 2.5.1` are fully operational inside `venv`.
   * No PyTorch (`torch`), `transformers`, or `sentence-transformers` were present, confirming the necessity of a pure ONNX Runtime pipeline.

---

## 4. Execution Boundary Confirmation

* Zero packages installed or updated.
* Zero model weights downloaded.
* Zero files created or deleted.
* Uvicorn backend process remained running uninterrupted.
