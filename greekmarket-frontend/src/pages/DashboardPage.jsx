// src/pages/DashboardPage.jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api/axios";
import logout from "../utils/logout";
import "../styles/DashboardPage.css";

export default function DashboardPage() {
  const [user, setUser] = useState(null);
  const [err, setErr] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      try {
        const { data } = await API.get("/me");
        setUser(data);
      } catch (e) {
        const status = e?.response?.status;
        const msg = e?.response?.data?.error || "Could not load your profile.";
        setErr(msg);
        if (status === 401) {
          localStorage.removeItem("token");
          setTimeout(() => navigate("/login"), 600);
        }
      }
    })();
  }, [navigate]);

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header">
        <img src="/greekvault-logo.png" alt="GreekVault" className="dashboard-logo" />
        <h2>Dashboard</h2>
        <button
          className="menu-btn"
          aria-label="Open menu"
          onClick={() => setMenuOpen(true)}
        >
          ☰
        </button>
      </header>

      {!user && !err && <div className="dashboard-loading">Loading…</div>}
      {err && <p className="dashboard-error">{err}</p>}

      {user && (
        <>
          {/* Profile card */}
          <section className="profile-card">
            <img
              src={user.profile_picture_url || "/default-avatar.png"}
              alt={`${user.first_name} ${user.last_name}`}
              className="profile-avatar"
            />
            <div className="profile-meta">
              <h3>{user.first_name} {user.last_name}</h3>
              <p>@{user.handle}</p>
              {user.chapter_name && (
                <p className="profile-chapter">
                  {user.chapter_name} ({user.chapter_role})
                </p>
              )}
            </div>
          </section>

          {/* Quick actions */}
          <section className="quick-actions">
            <a className="qa-btn primary" href="/create">Create Post</a>
            {!user.stripe_account_id && (
              <a className="qa-btn warn" href="/account">Complete Account Setup</a>
            )}
          </section>

          {/* Recent posts placeholder */}
          <section className="dashboard-section">
            <h4>Your recent posts</h4>
            <p className="muted">Coming soon — we’ll list your last few posts here.</p>
          </section>
        </>
      )}

      {/* Bottom sheet menu */}
      {menuOpen && (
        <>
          <div className="dash-backdrop" onClick={() => setMenuOpen(false)} />
          <div className="dash-sheet" role="dialog" aria-modal="true">
            <div className="dash-grabber" />
            <button
              className="sheet-item"
              onClick={() => { setMenuOpen(false); navigate("/purchases"); }}
            >
              Purchases
            </button>
            <button
              className="sheet-item"
              onClick={() => { setMenuOpen(false); navigate("/search"); }}
            >
              Search
            </button>
            <button
              className="sheet-item"
              onClick={() => { setMenuOpen(false); navigate("/create"); }}
            >
              Create Post
            </button>
            <hr className="sheet-sep" />
            <button className="sheet-item danger" onClick={logout}>
              Log out
            </button>
            <button className="sheet-cancel" onClick={() => setMenuOpen(false)}>
              Cancel
            </button>
          </div>
        </>
      )}
    </div>
  );
}
