// src/pages/SchoolPage.jsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import API from "../api/axios";
import "../styles/SchoolPage.css";

/* --- tiny helpers (unchanged UI) --- */
const badge = (text, tone = "default") => (
  <span className={`chip chip-${tone}`}>{text}</span>
);

const initialsCircle = (txt) => (
  <div className="avatar avatar-24">{txt}</div>
);


const toGreek = (name = "") => {
  const map = {
    alpha: "Α", beta: "Β", gamma: "Γ", delta: "Δ", epsilon: "Ε",
    zeta: "Ζ", eta: "Η", theta: "Θ", iota: "Ι", kappa: "Κ",
    lambda: "Λ", mu: "Μ", nu: "Ν", xi: "Ξ", omicron: "Ο",
    pi: "Π", rho: "Ρ", sigma: "Σ", tau: "Τ", upsilon: "Υ",
    phi: "Φ", chi: "Χ", psi: "Ψ", omega: "Ω",
  };

  const parts = name.toLowerCase().split(/\s+/).filter(Boolean);
  const out = [];
  for (const raw of parts) {
    // Skip words that are entirely parenthetical, e.g., "(beta)"
    if (/^\(.+\)$/.test(raw)) continue;
    const clean = raw.replace(/[()]/g, "");
    if (map[clean]) out.push(map[clean]);
    if (out.length === 3) break; // cap to 3 letters
  }
  if (out.length) return out.join("");

  // fallback: first two initials
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() || "")
    .join("");
};


const schoolAcronym = (name = "") => {
  // “Florida State University” -> “FSU”
  const words = name.split(/\s+/).filter(Boolean);
  const letters = words.map(w => w[0]?.toUpperCase() || "");
  return letters.slice(0, 3).join("");
};

export default function SchoolPage() {
  const { id: schoolIdParam } = useParams();
  const schoolId = Number(schoolIdParam);
  const navigate = useNavigate();

  const [school, setSchool] = useState(null);
  const [joined, setJoined] = useState(false);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  // Normalize backend payloads so render code stays the same.
  // Supports both:
  //  - { school: {...}, stats: {...}, chapters: [...] }
  //  - { school_id, name, domain, chapters: [...] }  (older shape)
  function normalizeSchool(payload) {
    if (!payload) return null;

    // New detailed endpoint shape
    if (payload.school) {
      const s = payload.school || {};
      const stats = payload.stats || {};
      const chapters = payload.chapters || [];
      return {
        ...s,
        // keep your component expectations:
        members: stats.members ?? 0,
        recent_posts: stats.recent_posts ?? 0,
        chapters,
      };
    }

    // Older/flat shape
    if (payload.school_id) return payload;
    if (payload.id) {
      return { ...payload, school_id: payload.id };
    }
    return null;
  }

  useEffect(() => {
    let mounted = true;

    (async () => {
      setLoading(true);
      setErr("");

      try {
        // Fetch school detail
        const { data } = await API.get(`/schools/${schoolId}`);
        const normalized = normalizeSchool(data);

        if (!mounted) return;

        if (!normalized?.school_id) {
          setErr("School not found.");
          setSchool(null);
          setLoading(false);
          return;
        }

        setSchool(normalized);

        // Prefer backend membership flag when available
        if (typeof data?.is_member === "boolean") {
          setJoined(data.is_member);
          return setLoading(false);
        }

        // Fallback: check /me only if backend didn't give membership
        try {
          const me = await API.get("/me");
          if (!mounted) return;
          setJoined(Number(me?.data?.school_id) === normalized.school_id);
        } catch {
          if (!mounted) return;
          setJoined(false);
        }
      } catch (e) {
        if (!mounted) return;
        setErr("Failed to load school.");
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [schoolId]);

  const chapters = useMemo(() => school?.chapters ?? [], [school]);

  const handleJoin = async () => {
    if (!school) return;
    try {
      // Use your backend join route so it persists across refresh
      await API.post(`/schools/${school.school_id}/join`);
      setJoined(true);
    } catch {
      // best-effort UX: silently ignore for now
    }
  };

  if (loading) {
    return (
      <div className="school-page">
        <header className="sp-header">
          <button className="btn ghost" onClick={() => navigate(-1)}>Back</button>
        </header>
        <div className="sp-loading">Loading…</div>
      </div>
    );
  }

  if (err) {
    return (
      <div className="school-page">
        <header className="sp-header">
          <button className="btn ghost" onClick={() => navigate(-1)}>Back</button>
        </header>
        <p className="sp-error">{err}</p>
      </div>
    );
  }

  const s = school;
  const acronym = schoolAcronym(s?.name || "");

  return (
    <div className="school-page">
      <header className="sp-header">
        <div className="sp-left">
          <div className="avatar avatar-40">{acronym}</div>
          <div className="sp-title">
            <h1>{s?.name}</h1>
            <div className="sp-sub">{s?.domain}</div>
          </div>
        </div>

        <div className="sp-right">
          <button className="btn ghost" onClick={() => navigate(-1)}>Back</button>
          {joined ? (
            <button className="btn success" disabled>Joined</button>
          ) : (
            <button className="btn primary" onClick={handleJoin}>Join School</button>
          )}
        </div>
      </header>

      <section className="sp-stats">
        <div className="stat-card">
          <div className="stat-value">{s?.members ?? 0}</div>
          <div className="stat-label">Members</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{(s?.chapters?.length) ?? 0}</div>
          <div className="stat-label">Chapters</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{s?.recent_posts ?? 0}</div>
          <div className="stat-label">Recent Posts</div>
        </div>
      </section>

      <section className="sp-section">
        <div className="sp-section-head">
          <h3>Chapters</h3>
          <div className="muted">{chapters.length} total</div>
        </div>

        <div className="chapter-list">
          {chapters.map((c) => (
            <button
              key={c.chapter_id}
              className="chapter-row"
              onClick={() => navigate(`/chapter/${c.chapter_id}`)}
            >
              <div className="row-left">
                {initialsCircle(toGreek(c.name) || (c.name?.slice(0, 2)?.toUpperCase() ?? "??"))}
                <div className="row-text">
                  <div className="row-title">
                    <span className="name">{c.name}</span>
                    {badge("Chapter", "neutral")}
                    {c.verified ? badge("Verified", "positive") : null}
                  </div>
                  <div className="row-sub">{c.type || "Chapter"}</div>
                </div>
              </div>
              <div className="row-right">
                <span className="chev">›</span>
              </div>
            </button>
          ))}

          {!chapters.length && (
            <div className="empty">No chapters yet.</div>
          )}
        </div>
      </section>
    </div>
  );
}
