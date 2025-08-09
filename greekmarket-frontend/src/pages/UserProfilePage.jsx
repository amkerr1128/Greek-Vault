// src/pages/UserProfilePage.jsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import API from "../api/axios";

export default function UserProfilePage() {
  const { id } = useParams();
  const [user, setUser] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const { data } = await API.get(`/user/${id}`); // your backend has this
        setUser(data);
      } catch (e) {
        setErr(e?.response?.data?.error || e.message || "Failed to load user.");
      }
    })();
  }, [id]);

  return (
    <div className="search-page">
      <h1>User</h1>
      {!user && !err && <p>Loading…</p>}
      {err && <p style={{ color: "#b91c1c" }}>{err}</p>}
      {user && (
        <div className="card-row">
          <div className="meta">
            <div className="title">{user.first_name} {user.last_name}</div>
            <div className="sub">@{user.handle} • School #{user.school_id ?? "—"}</div>
          </div>
        </div>
      )}
    </div>
  );
}
