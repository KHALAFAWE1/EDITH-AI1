import { useState, useEffect, useCallback } from "react";
import { api } from "../services/api";
import {
  FaMemory,
  FaBookOpen,
  FaCheckCircle,
  FaTimesCircle,
  FaShieldAlt,
  FaCogs,
  FaSpinner,
  FaUpload,
  FaTrash,
  FaSearch,
  FaPlay,
  FaUndo,
  FaDatabase,
  FaExchangeAlt
} from "react-icons/fa";

export default function TarsAdaptivePanel() {
  const [subTab, setSubTab] = useState("overview"); // overview | memory | knowledge | learning | improvements | permissions
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState("");

  // State containers
  const [coreStatus, setCoreStatus] = useState(null);
  const [memories, setMemories] = useState([]);
  const [memoryQuery, setMemoryQuery] = useState("");
  const [memoryTypeFilter, setMemoryTypeFilter] = useState("");
  const [newMemory, setNewMemory] = useState({
    subject: "",
    content: "",
    memory_type: "LONG_TERM",
    fact_or_inference: "FACT"
  });

  const [documents, setDocuments] = useState([]);
  const [knowledgeQuery, setKnowledgeQuery] = useState("");
  const [knowledgeHits, setKnowledgeHits] = useState([]);
  const [uploadFile, setUploadFile] = useState(null);
  const [docTitle, setDocTitle] = useState("");

  const [learningRecords, setLearningRecords] = useState([]);
  const [learningInput, setLearningInput] = useState("");
  const [learningSubject, setLearningSubject] = useState("");
  const [learningSource, setLearningSource] = useState("conversation");
  const [evalRuns, setEvalRuns] = useState([]);

  const [proposals, setProposals] = useState([]);
  const [newProposal, setNewProposal] = useState({
    title: "",
    problem_description: "",
    proposed_solution: "",
    action_category: "modify_project_code"
  });

  const [trainingStatus, setTrainingStatus] = useState(null);
  const [permissions, setPermissions] = useState([]);

  const fetchAllAdaptiveData = useCallback(async () => {
    try {
      const [coreRes, memRes, docRes, lrnRes, evalRes, propRes, trnRes, permRes] = await Promise.all([
        api.get("/tars/core/status"),
        api.get("/tars/memory"),
        api.get("/tars/knowledge/documents"),
        api.get("/tars/learning/records"),
        api.get("/tars/evaluation/runs"),
        api.get("/tars/improvements"),
        api.get("/tars/training/status"),
        api.get("/tars/permissions")
      ]);
      setCoreStatus(coreRes.data);
      setMemories(memRes.data.memories || []);
      setDocuments(docRes.data.documents || []);
      setLearningRecords(lrnRes.data.records || []);
      setEvalRuns(evalRes.data.runs || []);
      setProposals(propRes.data.proposals || []);
      setTrainingStatus(trnRes.data);
      setPermissions(permRes.data.permissions || []);
    } catch (err) {
      console.error("Adaptive panel load error:", err);
    }
  }, []);

  useEffect(() => {
    fetchAllAdaptiveData();
  }, [fetchAllAdaptiveData]);

  const showToast = (msg) => {
    setFeedback(msg);
    setTimeout(() => setFeedback(""), 4000);
  };

  // Handlers
  const handleUpdateRoutingPolicy = async (policy) => {
    try {
      await api.post("/tars/core/routing-config", { routing_policy: policy });
      showToast(`Model Router policy updated to ${policy}`);
      fetchAllAdaptiveData();
    } catch (err) {
      showToast("Failed to update routing policy");
    }
  };

  const handleStoreMemory = async (e) => {
    e.preventDefault();
    if (!newMemory.content.trim()) return;
    setLoading(true);
    try {
      const res = await api.post("/tars/memory", {
        ...newMemory,
        subject: newMemory.subject || "general",
        is_verified_fact: newMemory.fact_or_inference === "FACT"
      });
      showToast(res.data.message || "Memory stored");
      setNewMemory({ subject: "", content: "", memory_type: "LONG_TERM", fact_or_inference: "FACT" });
      fetchAllAdaptiveData();
    } catch (err) {
      showToast(err.response?.data?.detail || "Failed to store memory");
    } finally {
      setLoading(false);
    }
  };

  const handleSearchMemory = async () => {
    const res = await api.get("/tars/memory", {
      params: { query: memoryQuery, memory_type: memoryTypeFilter || undefined }
    });
    setMemories(res.data.memories || []);
  };

  const handleDeleteMemory = async (uid) => {
    await api.delete(`/tars/memory/${uid}`);
    showToast("Memory deleted");
    fetchAllAdaptiveData();
  };

  const handleUploadKnowledgeFile = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    setLoading(true);
    const fd = new FormData();
    fd.append("file", uploadFile);
    if (docTitle) fd.append("title", docTitle);
    try {
      const res = await api.post("/tars/knowledge/upload", fd);
      showToast(res.data.message || "Document ingested");
      setUploadFile(null);
      setDocTitle("");
      fetchAllAdaptiveData();
    } catch (err) {
      showToast(err.response?.data?.detail || "Document upload failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSearchKnowledge = async () => {
    if (!knowledgeQuery.trim()) return;
    const res = await api.get("/tars/knowledge/search", { params: { query: knowledgeQuery } });
    setKnowledgeHits(res.data.results || []);
  };

  const handleRunLearningPipeline = async (e) => {
    e.preventDefault();
    if (!learningInput.trim()) return;
    setLoading(true);
    try {
      const res = await api.post("/tars/learning/ingest", {
        raw_input: learningInput,
        subject_hint: learningSubject || undefined,
        source_type: learningSource,
        auto_verify: true
      });
      showToast(res.data.message);
      setLearningInput("");
      setLearningSubject("");
      fetchAllAdaptiveData();
    } catch (err) {
      showToast(err.response?.data?.detail || "Learning pipeline error");
    } finally {
      setLoading(false);
    }
  };

  const handleRunEvaluation = async () => {
    setLoading(true);
    try {
      const res = await api.post("/tars/evaluation/run", { eval_type: "comprehensive" });
      showToast(res.data.evaluation?.report_summary || "Evaluation complete");
      fetchAllAdaptiveData();
    } catch (err) {
      showToast("Evaluation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProposal = async (e) => {
    e.preventDefault();
    if (!newProposal.title.trim() || !newProposal.proposed_solution.trim()) return;
    setLoading(true);
    try {
      await api.post("/tars/improvements", newProposal);
      showToast("Proposal created and locked pending human review.");
      setNewProposal({
        title: "",
        problem_description: "",
        proposed_solution: "",
        action_category: "modify_project_code"
      });
      fetchAllAdaptiveData();
    } catch (err) {
      showToast("Failed to create proposal");
    } finally {
      setLoading(false);
    }
  };

  const handleProposalAction = async (proposalId, action) => {
    try {
      if (action === "test") {
        await api.post(`/tars/improvements/${proposalId}/test`, {});
      } else if (action === "approve") {
        await api.post(`/tars/improvements/${proposalId}/review`, { decision: "APPROVE" });
      } else if (action === "reject") {
        await api.post(`/tars/improvements/${proposalId}/review`, { decision: "REJECT" });
      } else if (action === "apply") {
        await api.post(`/tars/improvements/${proposalId}/apply`);
      } else if (action === "rollback") {
        await api.post(`/tars/improvements/${proposalId}/rollback`, { reason: "Manual operator rollback" });
      }
      showToast(`Proposal ${action.toUpperCase()} completed`);
      fetchAllAdaptiveData();
    } catch (err) {
      showToast(err.response?.data?.detail || `Action ${action} blocked by security gate`);
    }
  };

  const handlePrepareDataset = async () => {
    setLoading(true);
    try {
      const res = await api.post("/tars/training/prepare-dataset", {
        dataset_name: "tars_verified_dataset",
        user_approved: true
      });
      showToast(res.data.message);
      fetchAllAdaptiveData();
    } catch (err) {
      showToast("Failed to prepare dataset");
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePermission = async (scopeName, currentEnabled) => {
    try {
      await api.post("/tars/permissions/update", {
        scope_name: scopeName,
        enabled: !currentEnabled
      });
      showToast(`Permission '${scopeName}' updated`);
      fetchAllAdaptiveData();
    } catch (err) {
      showToast("Failed to update permission");
    }
  };

  const stageInfo = coreStatus?.learning_stage;
  const routingCfg = coreStatus?.routing_config;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
      {/* Sub-navigation bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "10px",
          background: "#12151e",
          padding: "12px 16px",
          borderRadius: "14px",
          border: "1px solid rgba(245, 158, 11, 0.2)"
        }}
      >
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {[
            { id: "overview", label: "Router & Stages", icon: <FaExchangeAlt /> },
            { id: "memory", label: "Memory System", icon: <FaMemory /> },
            { id: "knowledge", label: "Knowledge Docs", icon: <FaBookOpen /> },
            { id: "learning", label: "Learning & Eval", icon: <FaCheckCircle /> },
            { id: "improvements", label: "Improvement Gate", icon: <FaCogs /> },
            { id: "permissions", label: "Permissions & Training", icon: <FaShieldAlt /> }
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setSubTab(t.id)}
              style={{
                background: subTab === t.id ? "#f59e0b" : "#1a1e29",
                color: subTab === t.id ? "#090a0f" : "#9ca3af",
                border: "1px solid rgba(245, 158, 11, 0.2)",
                borderRadius: "8px",
                padding: "7px 13px",
                fontSize: "12px",
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                gap: "6px",
                cursor: "pointer"
              }}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {stageInfo && (
          <span className="badge badge-green" style={{ fontSize: "12px", padding: "6px 12px" }}>
            ⚡ {stageInfo.stage_name}
          </span>
        )}
      </div>

      {feedback && (
        <div
          style={{
            background: "rgba(245, 158, 11, 0.15)",
            border: "1px solid #f59e0b",
            color: "#f59e0b",
            padding: "10px 16px",
            borderRadius: "10px",
            fontSize: "13px",
            fontWeight: 600
          }}
        >
          {feedback}
        </div>
      )}

      {/* 1. OVERVIEW: HYBRID MODEL ROUTER & LEARNING STAGES */}
      {subTab === "overview" && (
        <div className="vision-grid">
          <div style={{ background: "#12151e", borderRadius: "16px", border: "1px solid rgba(245, 158, 11, 0.2)", padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
            <h3 style={{ color: "#fff", margin: 0, fontSize: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <FaExchangeAlt color="#f59e0b" /> Hybrid AI Core — Model Router
            </h3>
            <p style={{ color: "#9ca3af", fontSize: "12px", margin: 0 }}>
              Routes tasks between Local Ollama LLM, Cloud Gemini LLM, and TARS Local Knowledge Core with automatic fallback and private data redaction.
            </p>

            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {["HYBRID_AUTO", "LOCAL_FIRST", "CLOUD_FIRST", "LOCAL_ONLY"].map((pol) => (
                <button
                  key={pol}
                  onClick={() => handleUpdateRoutingPolicy(pol)}
                  style={{
                    background: routingCfg?.routing_policy === pol ? "#00ff99" : "#1a1e29",
                    color: routingCfg?.routing_policy === pol ? "#090a0f" : "#f3f4f6",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    padding: "8px 12px",
                    fontSize: "12px",
                    fontWeight: 700,
                    cursor: "pointer"
                  }}
                >
                  {pol}
                </button>
              ))}
            </div>

            <div style={{ background: "#1a1e29", borderRadius: "10px", padding: "12px", fontSize: "12px", color: "#f3f4f6", display: "flex", flexDirection: "column", gap: "6px" }}>
              <div>
                <strong>Local Ollama Provider:</strong>{" "}
                <span style={{ color: coreStatus?.providers?.local_ollama?.available ? "#00ff99" : "#f59e0b" }}>
                  {coreStatus?.providers?.local_ollama?.available
                    ? `ONLINE (${coreStatus.providers.local_ollama.models.join(", ") || "Ready"})`
                    : "STANDBY (Local Knowledge & Telemetry Core Active)"}
                </span>
              </div>
              <div>
                <strong>Cloud Gemini Provider:</strong>{" "}
                <span style={{ color: coreStatus?.providers?.cloud_gemini?.available ? "#00ff99" : "#9ca3af" }}>
                  {coreStatus?.providers?.cloud_gemini?.available ? "ONLINE (Server-Side Key Secured)" : "KEY NOT CONFIGURED"}
                </span>
              </div>
              <div>
                <strong>Privacy Guard:</strong>{" "}
                <span style={{ color: "#00ff99" }}>Active (Blocks/Redacts secrets before Cloud calls)</span>
              </div>
            </div>

            <h4 style={{ color: "#9ca3af", margin: "6px 0 0 0", fontSize: "12px", textTransform: "uppercase" }}>
              Recent Routing Decisions
            </h4>
            <div style={{ maxHeight: "200px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "6px" }}>
              {(coreStatus?.recent_routing_logs || []).map((log) => (
                <div key={log.routing_uid} style={{ background: "#1a1e29", padding: "8px 10px", borderRadius: "8px", fontSize: "11px", color: "#d1d5db" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "#f59e0b", fontWeight: 700 }}>
                    <span>{log.provider_chosen} ({log.model_name})</span>
                    <span>{log.latency_ms} ms</span>
                  </div>
                  <div style={{ marginTop: "2px", color: "#9ca3af" }}>{log.routing_reason}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Learning Stages Card */}
          <div style={{ background: "#12151e", borderRadius: "16px", border: "1px solid rgba(0, 255, 153, 0.2)", padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
            <h3 style={{ color: "#fff", margin: 0, fontSize: "16px" }}>
              TARS Adaptive Learning Stages (مراحل تطور تارس)
            </h3>
            {(stageInfo?.stages || []).map((st) => (
              <div
                key={st.stage}
                style={{
                  background: "#1a1e29",
                  borderRadius: "12px",
                  padding: "14px",
                  border: st.completed ? "1px solid #00ff99" : "1px solid rgba(255,255,255,0.08)"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <strong style={{ color: st.completed ? "#00ff99" : "#f59e0b", fontSize: "13px" }}>
                    {st.title_ar} ({st.title})
                  </strong>
                  <span className={`badge ${st.completed ? "badge-green" : "badge-red"}`} style={{ fontSize: "10px" }}>
                    {st.completed ? "VERIFIED ✓" : "IN PROGRESS"}
                  </span>
                </div>
                <ul style={{ margin: 0, paddingLeft: "18px", color: "#9ca3af", fontSize: "12px", lineHeight: "1.6" }}>
                  {st.capabilities.map((cap, idx) => (
                    <li key={idx}>{cap}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 2. MEMORY SYSTEM */}
      {subTab === "memory" && (
        <div className="vision-grid">
          <div style={{ background: "#12151e", borderRadius: "16px", border: "1px solid rgba(245, 158, 11, 0.2)", padding: "20px" }}>
            <h3 style={{ color: "#fff", marginTop: 0, fontSize: "16px" }}>Store Verified Memory / Fact</h3>
            <form onSubmit={handleStoreMemory} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <input
                type="text"
                placeholder="Subject (e.g., Operator Preference, Project Architecture)..."
                value={newMemory.subject}
                onChange={(e) => setNewMemory({ ...newMemory, subject: e.target.value })}
                style={{ background: "#1a1e29", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "10px", color: "#fff" }}
              />
              <textarea
                rows={3}
                placeholder="Memory content (Secrets/API keys are automatically blocked unless consented)..."
                value={newMemory.content}
                onChange={(e) => setNewMemory({ ...newMemory, content: e.target.value })}
                style={{ background: "#1a1e29", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "10px", color: "#fff" }}
              />
              <div style={{ display: "flex", gap: "10px" }}>
                <select
                  value={newMemory.memory_type}
                  onChange={(e) => setNewMemory({ ...newMemory, memory_type: e.target.value })}
                  style={{ flex: 1, background: "#1a1e29", color: "#fff", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "8px" }}
                >
                  <option value="LONG_TERM">Long-Term Memory</option>
                  <option value="SHORT_TERM">Short-Term Memory</option>
                  <option value="EPISODIC">Episodic Memory</option>
                  <option value="SEMANTIC">Semantic Memory</option>
                </select>
                <select
                  value={newMemory.fact_or_inference}
                  onChange={(e) => setNewMemory({ ...newMemory, fact_or_inference: e.target.value })}
                  style={{ flex: 1, background: "#1a1e29", color: "#fff", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "8px" }}
                >
                  <option value="FACT">Verified Fact (حقيقة مؤكدة)</option>
                  <option value="INFERENCE">AI Inference (استنتاج)</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={loading}
                style={{ background: "#f59e0b", color: "#090a0f", border: "none", borderRadius: "8px", padding: "10px", fontWeight: 700, cursor: "pointer" }}
              >
                Save to TARS Memory
              </button>
            </form>
          </div>

          <div style={{ background: "#12151e", borderRadius: "16px", border: "1px solid rgba(255,255,255,0.08)", padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                type="text"
                placeholder="Semantic memory search..."
                value={memoryQuery}
                onChange={(e) => setMemoryQuery(e.target.value)}
                style={{ flex: 1, background: "#1a1e29", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }}
              />
              <select
                value={memoryTypeFilter}
                onChange={(e) => setMemoryTypeFilter(e.target.value)}
                style={{ background: "#1a1e29", color: "#fff", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "8px" }}
              >
                <option value="">All Types</option>
                <option value="LONG_TERM">LONG_TERM</option>
                <option value="SHORT_TERM">SHORT_TERM</option>
                <option value="EPISODIC">EPISODIC</option>
                <option value="SEMANTIC">SEMANTIC</option>
              </select>
              <button
                onClick={handleSearchMemory}
                style={{ background: "#f59e0b", color: "#090a0f", border: "none", borderRadius: "8px", padding: "8px 14px", fontWeight: 700, cursor: "pointer" }}
              >
                <FaSearch />
              </button>
            </div>

            <div style={{ maxHeight: "340px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px" }}>
              {memories.map((m) => (
                <div key={m.memory_uid} style={{ background: "#1a1e29", padding: "12px", borderRadius: "10px", display: "flex", justifyContent: "space-between", gap: "10px" }}>
                  <div>
                    <div style={{ display: "flex", gap: "6px", alignItems: "center", marginBottom: "4px" }}>
                      <span className={`badge ${m.is_verified_fact ? "badge-green" : "badge-red"}`} style={{ fontSize: "10px" }}>
                        {m.fact_or_inference}
                      </span>
                      <span style={{ fontSize: "11px", color: "#f59e0b", fontWeight: 700 }}>
                        [{m.memory_type}] {m.subject}
                      </span>
                      {m.similarity !== undefined && (
                        <span style={{ fontSize: "10px", color: "#9ca3af" }}>Sim: {Math.round(m.similarity * 100)}%</span>
                      )}
                    </div>
                    <div style={{ fontSize: "13px", color: "#f3f4f6" }}>{m.content}</div>
                    <div style={{ fontSize: "10px", color: "#9ca3af", marginTop: "4px" }}>
                      Source: {m.source_type} ({m.source_reference})
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteMemory(m.memory_uid)}
                    style={{ background: "none", border: "none", color: "#ff3b5c", cursor: "pointer", alignSelf: "flex-start" }}
                    title="Delete Memory"
                  >
                    <FaTrash />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 3. KNOWLEDGE ACQUISITION MODULE (TXT, PDF, DOCX) */}
      {subTab === "knowledge" && (
        <div className="vision-grid">
          <div style={{ background: "#12151e", borderRadius: "16px", border: "1px solid rgba(245, 158, 11, 0.2)", padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
            <h3 style={{ color: "#fff", margin: 0, fontSize: "16px" }}>
              <FaUpload color="#f59e0b" /> Ingest Knowledge File (TXT, PDF, DOCX, MD)
            </h3>
            <form onSubmit={handleUploadKnowledgeFile} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <input
                type="text"
                placeholder="Document Title (optional)..."
                value={docTitle}
                onChange={(e) => setDocTitle(e.target.value)}
                style={{ background: "#1a1e29", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "10px", color: "#fff" }}
              />
              <input
                type="file"
                accept=".txt,.pdf,.docx,.md,.json"
                onChange={(e) => setUploadFile(e.target.files[0])}
                style={{ color: "#9ca3af", fontSize: "12px" }}
              />
              <button
                type="submit"
                disabled={!uploadFile || loading}
                style={{ background: "#f59e0b", color: "#090a0f", border: "none", borderRadius: "8px", padding: "10px", fontWeight: 700, cursor: "pointer" }}
              >
                Extract, Chunk & Index Document
              </button>
            </form>

            <h4 style={{ color: "#9ca3af", fontSize: "12px", margin: "8px 0 0 0" }}>Indexed Documents ({documents.length})</h4>
            <div style={{ maxHeight: "220px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px" }}>
              {documents.map((d) => (
                <div key={d.doc_uid} style={{ background: "#1a1e29", padding: "10px", borderRadius: "8px", fontSize: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "#fff", fontWeight: 700 }}>
                    <span>{d.title} ({d.file_type})</span>
                    <span style={{ color: "#00ff99" }}>{d.total_chunks} chunks</span>
                  </div>
                  {d.conflicts_count > 0 && (
                    <div style={{ color: "#ff3b5c", fontSize: "11px", marginTop: "4px" }}>
                      ⚠️ {d.conflicts_count} Cross-Source Conflict(s) Detected
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: "#12151e", borderRadius: "16px", border: "1px solid rgba(255,255,255,0.08)", padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
            <h3 style={{ color: "#fff", margin: 0, fontSize: "16px" }}>Semantic Passage Retrieval with Citations</h3>
            <div style={{ display: "flex", gap: "8px" }}>
              <input
                type="text"
                placeholder="Search across ingested documents..."
                value={knowledgeQuery}
                onChange={(e) => setKnowledgeQuery(e.target.value)}
                style={{ flex: 1, background: "#1a1e29", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "8px 12px", color: "#fff" }}
              />
              <button
                onClick={handleSearchKnowledge}
                style={{ background: "#f59e0b", color: "#090a0f", border: "none", borderRadius: "8px", padding: "8px 14px", fontWeight: 700, cursor: "pointer" }}
              >
                <FaSearch />
              </button>
            </div>
            <div style={{ maxHeight: "320px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px" }}>
              {knowledgeHits.map((hit) => (
                <div key={hit.chunk_uid} style={{ background: "#1a1e29", padding: "12px", borderRadius: "10px", fontSize: "12px" }}>
                  <div style={{ color: "#f59e0b", fontWeight: 700, marginBottom: "4px" }}>{hit.citation}</div>
                  <div style={{ color: "#f3f4f6", lineHeight: "1.6" }}>{hit.content}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 4. LEARNING PIPELINE & EVALUATION ENGINE */}
      {subTab === "learning" && (
        <div className="vision-grid">
          <div style={{ background: "#12151e", borderRadius: "16px", border: "1px solid rgba(245, 158, 11, 0.2)", padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
            <h3 style={{ color: "#fff", margin: 0, fontSize: "16px" }}>8-Step Verified Learning Pipeline</h3>
            <form onSubmit={handleRunLearningPipeline} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <input
                type="text"
                placeholder="Knowledge Subject..."
                value={learningSubject}
                onChange={(e) => setLearningSubject(e.target.value)}
                style={{ background: "#1a1e29", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "10px", color: "#fff" }}
              />
              <textarea
                rows={3}
                placeholder="Information or lesson to learn and verify via automatic comprehension quiz..."
                value={learningInput}
                onChange={(e) => setLearningInput(e.target.value)}
                style={{ background: "#1a1e29", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "10px", color: "#fff" }}
              />
              <button
                type="submit"
                disabled={loading}
                style={{ background: "#00ff99", color: "#090a0f", border: "none", borderRadius: "8px", padding: "10px", fontWeight: 700, cursor: "pointer" }}
              >
                Ingest, Generate Quiz & Verify Learning
              </button>
            </form>

            <div style={{ maxHeight: "220px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px" }}>
              {learningRecords.map((lr) => (
                <div key={lr.learning_uid} style={{ background: "#1a1e29", padding: "10px", borderRadius: "8px", fontSize: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <strong style={{ color: "#fff" }}>{lr.extracted_subject}</strong>
                    <span className={`badge ${lr.verification_passed ? "badge-green" : "badge-red"}`}>
                      {lr.approval_status} ({Math.round((lr.verification_score || 0) * 100)}%)
                    </span>
                  </div>
                  <div style={{ color: "#9ca3af", marginTop: "4px" }}>Quiz: {lr.verification_question}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: "#12151e", borderRadius: "16px", border: "1px solid rgba(0, 255, 153, 0.2)", padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ color: "#fff", margin: 0, fontSize: "16px" }}>Independent Evaluation Engine</h3>
              <button
                onClick={handleRunEvaluation}
                disabled={loading}
                style={{ background: "#f59e0b", color: "#090a0f", border: "none", borderRadius: "8px", padding: "8px 14px", fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" }}
              >
                {loading ? <FaSpinner className="spin" /> : <FaPlay />} Run Benchmark Suite
              </button>
            </div>
            <div style={{ maxHeight: "320px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px" }}>
              {evalRuns.map((run) => (
                <div key={run.eval_uid} style={{ background: "#1a1e29", padding: "12px", borderRadius: "10px", fontSize: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "#00ff99", fontWeight: 700 }}>
                    <span>Score: {Math.round(run.overall_score * 100)}% ({run.passed_tests}/{run.total_tests} passed)</span>
                    <span>Task Success: {Math.round(run.task_success_rate * 100)}%</span>
                  </div>
                  <div style={{ color: "#d1d5db", marginTop: "4px" }}>{run.report_summary}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 5. CONTROLLED SELF-IMPROVEMENT (HUMAN APPROVAL GATE) */}
      {subTab === "improvements" && (
        <div className="vision-grid">
          <div style={{ background: "#12151e", borderRadius: "16px", border: "1px solid rgba(245, 158, 11, 0.2)", padding: "20px" }}>
            <h3 style={{ color: "#fff", marginTop: 0, fontSize: "16px" }}>Propose Controlled Improvement</h3>
            <form onSubmit={handleCreateProposal} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <input
                type="text"
                placeholder="Proposal Title..."
                value={newProposal.title}
                onChange={(e) => setNewProposal({ ...newProposal, title: e.target.value })}
                style={{ background: "#1a1e29", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "10px", color: "#fff" }}
              />
              <textarea
                rows={2}
                placeholder="Problem explanation..."
                value={newProposal.problem_description}
                onChange={(e) => setNewProposal({ ...newProposal, problem_description: e.target.value })}
                style={{ background: "#1a1e29", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "10px", color: "#fff" }}
              />
              <textarea
                rows={2}
                placeholder="Proposed solution..."
                value={newProposal.proposed_solution}
                onChange={(e) => setNewProposal({ ...newProposal, proposed_solution: e.target.value })}
                style={{ background: "#1a1e29", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "10px", color: "#fff" }}
              />
              <select
                value={newProposal.action_category}
                onChange={(e) => setNewProposal({ ...newProposal, action_category: e.target.value })}
                style={{ background: "#1a1e29", color: "#fff", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", padding: "8px" }}
              >
                <option value="modify_project_code">Modify Project Code (Requires Approval)</option>
                <option value="change_base_model">Change Base Model (Requires Approval)</option>
                <option value="fine_tune_model">Fine-Tune Model (Requires Approval)</option>
                <option value="alter_database_schema">Alter Database Schema (Requires Approval)</option>
                <option value="install_packages">Install Packages (Requires Approval)</option>
                <option value="modify_permissions">Modify Permissions (Requires Approval)</option>
              </select>
              <button
                type="submit"
                style={{ background: "#f59e0b", color: "#090a0f", border: "none", borderRadius: "8px", padding: "10px", fontWeight: 700, cursor: "pointer" }}
              >
                Stage Proposal in Sandbox
              </button>
            </form>
          </div>

          <div style={{ background: "#12151e", borderRadius: "16px", border: "1px solid rgba(255,255,255,0.08)", padding: "20px", display: "flex", flexDirection: "column", gap: "10px" }}>
            <h3 style={{ color: "#fff", margin: 0, fontSize: "16px" }}>Human Approval Gate ({proposals.length})</h3>
            <div style={{ maxHeight: "340px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "10px" }}>
              {proposals.map((p) => (
                <div key={p.proposal_id} style={{ background: "#1a1e29", padding: "12px", borderRadius: "10px", fontSize: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <strong style={{ color: "#fff" }}>{p.title}</strong>
                    <span className="badge badge-red">{p.risk_level} | {p.approval_status}</span>
                  </div>
                  <div style={{ color: "#9ca3af", margin: "4px 0" }}>{p.proposed_solution}</div>
                  <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "8px" }}>
                    <button onClick={() => handleProposalAction(p.proposal_id, "test")} style={{ background: "#374151", color: "#fff", border: "none", borderRadius: "6px", padding: "5px 10px", cursor: "pointer", fontSize: "11px" }}>
                      1. Sandbox Test
                    </button>
                    <button onClick={() => handleProposalAction(p.proposal_id, "approve")} style={{ background: "#00ff99", color: "#090a0f", border: "none", borderRadius: "6px", padding: "5px 10px", cursor: "pointer", fontSize: "11px", fontWeight: 700 }}>
                      2. Approve
                    </button>
                    <button onClick={() => handleProposalAction(p.proposal_id, "reject")} style={{ background: "#ff3b5c", color: "#fff", border: "none", borderRadius: "6px", padding: "5px 10px", cursor: "pointer", fontSize: "11px" }}>
                      Reject
                    </button>
                    <button onClick={() => handleProposalAction(p.proposal_id, "apply")} style={{ background: "#f59e0b", color: "#090a0f", border: "none", borderRadius: "6px", padding: "5px 10px", cursor: "pointer", fontSize: "11px", fontWeight: 700 }}>
                      3. Apply
                    </button>
                    <button onClick={() => handleProposalAction(p.proposal_id, "rollback")} style={{ background: "#1f2937", color: "#9ca3af", border: "1px solid #374151", borderRadius: "6px", padding: "5px 10px", cursor: "pointer", fontSize: "11px" }}>
                      <FaUndo /> Rollback
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 6. PERMISSIONS & DATASET TRAINING READINESS */}
      {subTab === "permissions" && (
        <div className="vision-grid">
          <div style={{ background: "#12151e", borderRadius: "16px", border: "1px solid rgba(245, 158, 11, 0.2)", padding: "20px", display: "flex", flexDirection: "column", gap: "10px" }}>
            <h3 style={{ color: "#fff", margin: 0, fontSize: "16px" }}>Scoped Security Permissions</h3>
            {permissions.map((perm) => (
              <div key={perm.scope_name} style={{ background: "#1a1e29", padding: "10px 12px", borderRadius: "8px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ color: "#fff", fontSize: "13px", fontWeight: 700 }}>{perm.scope_name}</div>
                  <div style={{ color: "#9ca3af", fontSize: "11px" }}>{perm.description}</div>
                </div>
                <button
                  onClick={() => handleTogglePermission(perm.scope_name, perm.enabled)}
                  style={{
                    background: perm.enabled ? "rgba(0, 255, 153, 0.15)" : "rgba(255, 59, 92, 0.15)",
                    color: perm.enabled ? "#00ff99" : "#ff3b5c",
                    border: `1px solid ${perm.enabled ? "#00ff99" : "#ff3b5c"}`,
                    borderRadius: "6px",
                    padding: "5px 12px",
                    fontSize: "11px",
                    fontWeight: 700,
                    cursor: "pointer"
                  }}
                >
                  {perm.enabled ? "ENABLED" : "DISABLED"}
                </button>
              </div>
            ))}
          </div>

          <div style={{ background: "#12151e", borderRadius: "16px", border: "1px solid rgba(0, 255, 153, 0.2)", padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
            <h3 style={{ color: "#fff", margin: 0, fontSize: "16px" }}>
              <FaDatabase color="#00ff99" /> Dataset Curation & Fine-Tuning Readiness
            </h3>
            <div style={{ background: "#1a1e29", padding: "12px", borderRadius: "10px", fontSize: "12px", color: "#d1d5db" }}>
              <div><strong>Status:</strong> <span style={{ color: "#f59e0b" }}>{trainingStatus?.honest_status}</span></div>
              <p style={{ color: "#9ca3af", margin: "6px 0" }}>{trainingStatus?.explanation}</p>
              <div>
                <strong>Hardware:</strong> {trainingStatus?.hardware?.cpu_cores} Cores | {trainingStatus?.hardware?.ram_total_gb} GB RAM | CUDA GPU: {trainingStatus?.hardware?.cuda_gpu_available ? "YES" : "NO"}
              </div>
            </div>
            <button
              onClick={handlePrepareDataset}
              disabled={loading}
              style={{ background: "#00ff99", color: "#090a0f", border: "none", borderRadius: "8px", padding: "10px", fontWeight: 700, cursor: "pointer" }}
            >
              Clean, Deduplicate & Export Verified JSONL Dataset
            </button>
            <div style={{ maxHeight: "180px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "6px" }}>
              {(trainingStatus?.datasets || []).map((ds) => (
                <div key={ds.dataset_version} style={{ background: "#1a1e29", padding: "8px 10px", borderRadius: "8px", fontSize: "11px", color: "#f3f4f6" }}>
                  <strong>{ds.dataset_version}</strong> — Clean: {ds.clean_record_count} | Duplicates Removed: {ds.duplicates_removed} | Noise Removed: {ds.noisy_removed}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
