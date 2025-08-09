// src/pages/ChapterPage.jsx
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import API from "../api/axios";
import "../styles/ChapterPage.css";

// Reuse the same Greek-letter logic you liked on SchoolPage
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
    // ignore parenthetical nicknames like (Beta)
    if (/^\(.+\)$/.test(raw)) continue;
    const clean = raw.replace(/[()]/g, "");
    if (map[clean]) out.push(map[clean]);
    if (out.length === 3) break; // cap at 3 glyphs
  }
  if (out.length) return out.join("");

  // fallback to first two initials
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0]?.toUpperCase() || "")
    .join("");
};

export default function ChapterPage() {
  const { id: chapterIdParam } = useParams();
  const chapterId = Number(chapterIdParam);
  const navigate = useNavigate();

  const [data, setData] = useState(null);      // { chapter, is_member, stats, recent_posts, members }
  const [joining, setJoining] = useState(false);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setErr("");
      try {
        // New backend endpoint below in routes.py
        const { data } = await API.get(`/chapters/${chapterId}`);
        if (!mounted) return;
        setData(data);
      } catch (e) {
        if (!mounted) return;
        setErr(e?.response?.data?.error || "Failed to load chapter.");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [chapterId]);

  const c = data?.chapter;
  const members = useMemo(() => data?.members ?? [], [data]);
  const posts = useMemo(() => data?.recent_posts ?? [], [data]);

  async function join() {
    try {
      setJoining(true);
      await API.post(`/chapters/${chapterId}/join`);
      // optimistic UI
      setData(d => d ? { ...d, is_member: true, stats: { ...d.stats, members: (d.stats?.members ?? 0) + 1 } } : d);
    } catch (e) {
      setErr(e?.response?.data?.error || "Failed to join chapter.");
    } finally {
      setJoining(false);
    }
  }

  if (loading) {
    return (
      <div className="chapter-page">
        <header className="cp-header">
          <button className="btn ghost" onClick={() => navigate(-1)}>Back</button>
        </header>
        <div className="cp-loading">Loading…</div>
      </div>
    );
  }

  if (err || !c) {
    return (
      <div className="chapter-page">
        <header className="cp-header">
          <button className="btn ghost" onClick={() => navigate(-1)}>Back</button>
        </header>
        <p className="cp-error">{err || "Chapter not found."}</p>
      </div>
    );
  }

  const greek = toGreek(c.name);

  return (
    <div className="chapter-page">
      <header className="cp-header">
        <div className="cp-left">
          <div className="cp-avatar">{greek}</div>
          <div className="cp-title">
            <h1>{c.name}</h1>
            <div className="cp-sub">
              {c.type || "Chapter"} {c.nickname ? <>• “{c.nickname}”</> : null}
            </div>
          </div>
        </div>
        <div className="cp-right">
          <button className="btn ghost" onClick={() => navigate(-1)}>Back</button>
          {data?.is_member ? (
            <button className="btn success" disabled>Joined</button>
          ) : (
            <button className="btn primary" onClick={join} disabled={joining}>
              {joining ? "Joining…" : "Join Chapter"}
            </button>
          )}
        </div>
      </header>

      <section className="cp-stats">
        <div className="stat-card">
          <div className="stat-value">{data?.stats?.members ?? 0}</div>
          <div className="stat-label">Members</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data?.stats?.recent_posts ?? 0}</div>
          <div className="stat-label">Recent Posts</div>
        </div>
      </section>

      <section className="cp-section">
        <div className="cp-section-head">
          <h3>Recent posts</h3>
          <div className="muted">{posts.length}</div>
        </div>
        {posts.length === 0 ? (
          <div className="cp-empty">No recent posts yet.</div>
        ) : (
          <div className="cp-posts">
            {posts.map(p => (
              <a key={p.post_id} className="post-card" href={`/post/${p.post_id}`}>
                <div className="post-thumb">
                  {p.image_url ? <img src={p.image_url} alt="" /> : <div className="thumb-fallback">No image</div>}
                </div>
                <div className="post-meta">
                  <div className="post-title">{p.title}</div>
                  <div className="post-sub">
                    <span className="pill">{p.type}</span>
                    {p.price != null && <span className="pill">${Number(p.price).toFixed(2)}</span>}
                    <span className="pill handle">@{p.user_handle}</span>
                  </div>
                </div>
              </a>
            ))}
          </div>
        )}
      </section>

      <section className="cp-section">
        <div className="cp-section-head">
          <h3>Members</h3>
          <div className="muted">{members.length}</div>
        </div>
        {members.length === 0 ? (
          <div className="cp-empty">No members yet.</div>
        ) : (
          <ul className="cp-members">
            {members.map(m => (
              <li key={m.user_id} className="member-row">
                <img className="member-avatar" src={m.profile_picture_url || "/default-avatar.png"} alt="" />
                <div className="member-meta">
                  <div className="member-name">
                    {m.first_name} {m.last_name} <span className="muted">@{m.handle}</span>
                  </div>
                  <div className="member-role">{m.role}</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
