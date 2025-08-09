// src/pages/OnboardingPage.jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api/axios";
import "../styles/OnboardingPage.css";

export default function OnboardingPage() {
  const [query, setQuery] = useState("");
  const [schools, setSchools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [joining, setJoining] = useState(0);
  const [err, setErr] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        setLoading(true);
        const { data } = await API.get("/schools");
        if (!active) return;
        setSchools(data);
      } catch (e) {
        setErr(e?.response?.data?.error || "Failed to load schools.");
      } finally {
        setLoading(false);
      }
    })();
    return () => { active = false; };
  }, []);

  const filtered = schools.filter(s => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return s.name.toLowerCase().includes(q) || s.domain.toLowerCase().includes(q);
  });

  async function join(schoolId) {
    try {
      setJoining(schoolId);
      await API.post(`/schools/${schoolId}/join`);
      // after joining, take the user to that school's page or back to create
      navigate(`/school/${schoolId}`, { replace: true });
    } catch (e) {
      setErr(e?.response?.data?.error || "Failed to join school.");
      setJoining(0);
    }
  }

  return (
    <div className="onboard-wrap">
      <h1>Choose your school</h1>
      <p className="onboard-sub">You’ll use this to see school posts and create your own.</p>

      <div className="onboard-search">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search schools by name or domain…"
          aria-label="Search schools"
        />
      </div>

      {err && <div className="onboard-error">{err}</div>}

      {loading ? (
        <div className="onboard-loading">Loading schools…</div>
      ) : filtered.length === 0 ? (
        <div className="onboard-empty">No schools match “{query}”.</div>
      ) : (
        <ul className="onboard-list">
          {filtered.map(s => (
            <li key={s.id} className="onboard-item">
              <div className="onboard-meta">
                <div className="onboard-name">{s.name}</div>
                <div className="onboard-domain">{s.domain}</div>
              </div>
              <div className="onboard-actions">
                <button
                  className="btn-secondary"
                  onClick={() => navigate(`/school/${s.id}`)}
                >
                  Open
                </button>
                <button
                  className="btn-primary"
                  disabled={joining === s.id}
                  onClick={() => join(s.id)}
                >
                  {joining === s.id ? "Joining…" : "Join"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
