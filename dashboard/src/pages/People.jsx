import { useEffect, useState } from "react";
import MainLayout from "../layouts/MainLayout";
import PersonCard from "../components/PersonCard";
import { api } from "../services/api";
import { FaUserPlus, FaSearch, FaTimes, FaCamera, FaIdCard, FaSpinner, FaUsers } from "react-icons/fa";

export default function People() {
  const [people, setPeople] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState({ message: "", isError: false });

  // Form State
  const [formData, setFormData] = useState({
    full_name: "",
    person_type: "Student",
    department: "",
    position: "",
    subjects: "",
    phone: "",
    email: "",
    office: "",
    notes: ""
  });
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);

  // Fetch People from Backend
  const fetchPeople = async () => {
    try {
      setLoading(true);
      const res = await api.get("/people");
      setPeople(res.data);
    } catch (err) {
      console.error("Failed to load people:", err);
      setFeedback({ message: "فشل تحميل قائمة الأشخاص من الخادم", isError: true });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPeople();
  }, []);

  // Handle Photo Selection
  const handlePhotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedPhoto(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPhotoPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  // Handle Form Submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.full_name.trim()) {
      alert("يرجى إدخال اسم الشخص");
      return;
    }
    if (!selectedPhoto) {
      alert("يرجى اختيار صورة واضحة للوجه");
      return;
    }

    try {
      setSubmitting(true);
      setFeedback({ message: "", isError: false });

      const data = new FormData();
      data.append("full_name", formData.full_name);
      data.append("person_type", formData.person_type);
      data.append("department", formData.department);
      data.append("position", formData.position);
      data.append("subjects", formData.subjects);
      data.append("phone", formData.phone);
      data.append("email", formData.email);
      data.append("office", formData.office);
      data.append("notes", formData.notes);
      data.append("photo", selectedPhoto);

      const res = await api.post("/people/register", data);

      if (res.data.success || res.status === 200) {
        setFeedback({ message: "تم تسجيل الشخص واستخراج بصمة الوجه بنجاح!", isError: false });
        setIsModalOpen(false);
        // Reset Form
        setFormData({
          full_name: "",
          person_type: "Student",
          department: "",
          position: "",
          subjects: "",
          phone: "",
          email: "",
          office: "",
          notes: ""
        });
        setSelectedPhoto(null);
        setPhotoPreview(null);
        fetchPeople();
      }
    } catch (err) {
      console.error(err);
      const errMsg = err.response?.data?.detail || "حدث خطأ أثناء تسجيل الشخص. تأكد من وضوح الوجه في الصورة.";
      setFeedback({ message: errMsg, isError: true });
    } finally {
      setSubmitting(false);
    }
  };

  // Delete Person
  const handleDelete = async (id, name) => {
    if (!window.confirm(`هل أنت متأكد من رغبتك في حذف ${name} وبصماته من النظام؟`)) {
      return;
    }

    try {
      await api.delete(`/people/${id}`);
      setFeedback({ message: `تم حذف ${name} بنجاح`, isError: false });
      fetchPeople();
    } catch (err) {
      console.error("Delete failed:", err);
      setFeedback({ message: "فشل حذف الشخص", isError: true });
    }
  };

  // Filtered List
  const filteredPeople = people.filter((p) => {
    const matchesSearch =
      p.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.department?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.position?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesType = typeFilter === "ALL" || (p.person_type || "").toUpperCase() === typeFilter.toUpperCase();

    return matchesSearch && matchesType;
  });

  return (
    <MainLayout>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "22px" }}>
        <div>
          <h1 className="title" style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaUsers style={{ color: "#00d4ff" }} /> Biometric Identity Database
          </h1>
          <p className="subtitle">Manage registered personnel, roles, and facial recognition embeddings</p>
        </div>

        <button
          onClick={() => {
            setFeedback({ message: "", isError: false });
            setIsModalOpen(true);
          }}
          style={{
            background: "linear-gradient(135deg, #00d4ff 0%, #0077ff 100%)",
            color: "#050816",
            border: "none",
            borderRadius: "10px",
            padding: "12px 20px",
            fontWeight: 700,
            fontSize: "14px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            cursor: "pointer",
            boxShadow: "0 4px 15px rgba(0, 212, 255, 0.4)"
          }}
        >
          <FaUserPlus size={16} /> Register New Subject
        </button>
      </div>

      {/* Feedback Banner */}
      {feedback.message && (
        <div
          style={{
            background: feedback.isError ? "rgba(255, 59, 92, 0.15)" : "rgba(0, 255, 153, 0.15)",
            border: `1px solid ${feedback.isError ? "#ff3b5c" : "#00ff99"}`,
            color: feedback.isError ? "#ff3b5c" : "#00ff99",
            padding: "12px 20px",
            borderRadius: "10px",
            marginBottom: "20px",
            fontSize: "14px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center"
          }}
        >
          <span>{feedback.message}</span>
          <button onClick={() => setFeedback({ message: "", isError: false })} style={{ background: "none", border: "none", color: "inherit", cursor: "pointer" }}>
            <FaTimes />
          </button>
        </div>
      )}

      {/* Controls Bar: Search & Filter */}
      <div
        style={{
          display: "flex",
          gap: "15px",
          marginBottom: "25px",
          background: "#111827",
          padding: "14px 18px",
          borderRadius: "12px",
          border: "1px solid rgba(0, 212, 255, 0.15)"
        }}
      >
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "10px", background: "#192033", padding: "0 14px", borderRadius: "8px" }}>
          <FaSearch color="#8b9bb4" />
          <input
            type="text"
            placeholder="Search by name, department, position..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              background: "transparent",
              border: "none",
              color: "#fff",
              padding: "10px 0",
              width: "100%",
              outline: "none",
              fontSize: "14px"
            }}
          />
        </div>

        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          style={{
            background: "#192033",
            color: "#fff",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "8px",
            padding: "0 16px",
            outline: "none",
            cursor: "pointer"
          }}
        >
          <option value="ALL">All Roles ({people.length})</option>
          <option value="Student">Students</option>
          <option value="Teacher">Teachers / Professors</option>
          <option value="Employee">Staff / Employees</option>
          <option value="Security">Security / Admin</option>
        </select>
      </div>

      {/* Grid of Personnel Cards */}
      {loading ? (
        <div style={{ textAlign: "center", padding: "60px 0", color: "#00d4ff" }}>
          <FaSpinner className="spin" size={32} />
          <p style={{ marginTop: "15px", color: "#8b9bb4" }}>Loading biometric registry...</p>
        </div>
      ) : filteredPeople.length === 0 ? (
        <div
          style={{
            textAlign: "center",
            padding: "60px 20px",
            background: "#111827",
            borderRadius: "16px",
            border: "1px dashed rgba(255,255,255,0.1)",
            color: "#8b9bb4"
          }}
        >
          <FaIdCard size={42} style={{ marginBottom: "12px", color: "#00d4ff" }} />
          <h3>No Subjects Found</h3>
          <p style={{ fontSize: "14px", marginTop: "4px" }}>
            {searchTerm ? "No matching records found for your search criteria." : "No personnel registered yet. Click 'Register New Subject' to begin."}
          </p>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: "20px"
          }}
        >
          {filteredPeople.map((person) => (
            <PersonCard key={person.id} person={person} onDelete={handleDelete} />
          ))}
        </div>
      )}

      {/* Registration Modal */}
      {isModalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            background: "rgba(0, 0, 0, 0.8)",
            backdropFilter: "blur(8px)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            zIndex: 1000,
            padding: "20px"
          }}
        >
          <div
            style={{
              background: "#111827",
              borderRadius: "20px",
              border: "1px solid rgba(0, 212, 255, 0.3)",
              width: "100%",
              maxWidth: "650px",
              maxHeight: "90vh",
              overflowY: "auto",
              padding: "28px",
              boxShadow: "0 20px 50px rgba(0, 0, 0, 0.7)",
              position: "relative"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
              <h2 style={{ color: "#fff", fontSize: "20px", display: "flex", alignItems: "center", gap: "10px" }}>
                <FaUserPlus color="#00d4ff" /> Register New Subject
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                style={{ background: "none", border: "none", color: "#8b9bb4", fontSize: "18px", cursor: "pointer" }}
              >
                <FaTimes />
              </button>
            </div>

            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {/* Photo Upload Box */}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  padding: "16px",
                  background: "#192033",
                  borderRadius: "12px",
                  border: "2px dashed rgba(0, 212, 255, 0.3)",
                  position: "relative"
                }}
              >
                {photoPreview ? (
                  <div style={{ position: "relative", width: "120px", height: "120px" }}>
                    <img
                      src={photoPreview}
                      alt="Preview"
                      style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: "12px", border: "2px solid #00ff99" }}
                    />
                    <label
                      htmlFor="photo-upload"
                      style={{
                        position: "absolute",
                        bottom: "-6px",
                        right: "-6px",
                        background: "#00d4ff",
                        color: "#050816",
                        borderRadius: "50%",
                        padding: "6px",
                        cursor: "pointer"
                      }}
                    >
                      <FaCamera size={12} />
                    </label>
                  </div>
                ) : (
                  <label htmlFor="photo-upload" style={{ cursor: "pointer", textAlign: "center" }}>
                    <FaCamera size={36} color="#00d4ff" style={{ marginBottom: "8px" }} />
                    <p style={{ color: "#fff", fontSize: "14px", fontWeight: 600 }}>Click to Upload Face Photo</p>
                    <p style={{ color: "#8b9bb4", fontSize: "12px" }}>InsightFace will compute 512-dim embedding</p>
                  </label>
                )}
                <input
                  id="photo-upload"
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoChange}
                  style={{ display: "none" }}
                />
              </div>

              {/* Input Fields */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                <div>
                  <label style={{ display: "block", color: "#8b9bb4", fontSize: "12px", marginBottom: "4px" }}>Full Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Ahmed Ali"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    style={{ width: "100%", padding: "10px 12px", background: "#192033", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", outline: "none" }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", color: "#8b9bb4", fontSize: "12px", marginBottom: "4px" }}>Person Type</label>
                  <select
                    value={formData.person_type}
                    onChange={(e) => setFormData({ ...formData, person_type: e.target.value })}
                    style={{ width: "100%", padding: "10px 12px", background: "#192033", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", outline: "none" }}
                  >
                    <option value="Student">Student</option>
                    <option value="Teacher">Teacher / Professor</option>
                    <option value="Employee">Staff / Employee</option>
                    <option value="Security">Security / Admin</option>
                    <option value="Visitor">Visitor</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: "block", color: "#8b9bb4", fontSize: "12px", marginBottom: "4px" }}>Department</label>
                  <input
                    type="text"
                    placeholder="e.g. Computer Science"
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    style={{ width: "100%", padding: "10px 12px", background: "#192033", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", outline: "none" }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", color: "#8b9bb4", fontSize: "12px", marginBottom: "4px" }}>Position</label>
                  <input
                    type="text"
                    placeholder="e.g. AI Researcher / 4th Year"
                    value={formData.position}
                    onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                    style={{ width: "100%", padding: "10px 12px", background: "#192033", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", outline: "none" }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", color: "#8b9bb4", fontSize: "12px", marginBottom: "4px" }}>Email</label>
                  <input
                    type="email"
                    placeholder="e.g. subject@edith.ai"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    style={{ width: "100%", padding: "10px 12px", background: "#192033", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", outline: "none" }}
                  />
                </div>

                <div>
                  <label style={{ display: "block", color: "#8b9bb4", fontSize: "12px", marginBottom: "4px" }}>Phone</label>
                  <input
                    type="text"
                    placeholder="e.g. +20 10xxxxxxxx"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    style={{ width: "100%", padding: "10px 12px", background: "#192033", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", outline: "none" }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: "block", color: "#8b9bb4", fontSize: "12px", marginBottom: "4px" }}>Notes / Access Permissions</label>
                <textarea
                  rows="2"
                  placeholder="Special access level, tags, or notes..."
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  style={{ width: "100%", padding: "10px 12px", background: "#192033", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", color: "#fff", outline: "none", resize: "none" }}
                />
              </div>

              {/* Submit Buttons */}
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  style={{ background: "#192033", color: "#8b9bb4", border: "none", padding: "10px 18px", borderRadius: "8px", cursor: "pointer" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  style={{
                    background: "linear-gradient(135deg, #00d4ff 0%, #0077ff 100%)",
                    color: "#050816",
                    fontWeight: 700,
                    border: "none",
                    padding: "10px 24px",
                    borderRadius: "8px",
                    cursor: submitting ? "not-allowed" : "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    opacity: submitting ? 0.7 : 1
                  }}
                >
                  {submitting ? <FaSpinner className="spin" /> : <FaUserPlus />}
                  {submitting ? "Extracting Embeddings..." : "Register Subject"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </MainLayout>
  );
}