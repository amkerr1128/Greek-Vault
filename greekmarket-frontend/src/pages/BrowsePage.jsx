// src/pages/BrowsePage.jsx
import { useEffect, useMemo, useState } from "react";
import API from "../api/axios";
import PostCard from "../components/PostCard";
import BottomNav from "../components/BottomNav";
import "../styles/BrowsePage.css";

const TYPES = ["all", "apparel", "accessories", "stickers", "tickets", "other"];
const SORTS = [
  { value: "new", label: "Newest" },
  { value: "price", label: "Price: Low → High" },
  { value: "-price", label: "Price: High → Low" },
];

function SkeletonCard() {
  return (
    <div className="post-card skeleton">
      <div className="skeleton-img" />
      <div className="skeleton-line" />
      <div className="skeleton-line short" />
    </div>
  );
}

function BrowsePage() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [type, setType] = useState("all");
  const [sort, setSort] = useState("new");
  const [view, setView] = useState("grid"); // grid | list

  const filtered = useMemo(() => {
    let p = posts;
    if (q.trim()) {
      const s = q.trim().toLowerCase();
      p = p.filter(
        (x) =>
          x.title?.toLowerCase().includes(s) ||
          x.description?.toLowerCase().includes(s) ||
          x.user_handle?.toLowerCase().includes(s)
      );
    }
    return p;
  }, [posts, q]);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const token = localStorage.getItem("token");
        if (token) {
          const me = await API.get("/me");
          const schoolId = me.data.school_id;
          const params = new URLSearchParams();
          if (type !== "all") params.set("type", type);
          if (sort === "price") params.set("sort", "price");
          else if (sort === "-price") params.set("sort", "-price");
          const { data } = await API.get(`/posts/${schoolId}${params.toString() ? `?${params}` : ""}`);
          setPosts(data);
        } else {
          const { data } = await API.get("/activity/posts");
          setPosts(data);
        }
      } catch (e) {
        console.error("Error fetching posts:", e);
        setPosts([]);
      } finally {
        setLoading(false);
      }
    })();
  }, [type, sort]);

  return (
    <div className="browse-wrap">
      {/* Top bar */}
      <header className="browse-topbar">
        <h1>Browse</h1>
        <div className="right-controls">
          <div className="searchbox">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search posts, descriptions, @handles…"
              aria-label="Search"
            />
          </div>
          <div className="view-toggle">
            <button
              className={view === "grid" ? "active" : ""}
              onClick={() => setView("grid")}
              title="Grid view"
            >
              ⬛⬛
            </button>
            <button
              className={view === "list" ? "active" : ""}
              onClick={() => setView("list")}
              title="List view"
            >
              ☰
            </button>
          </div>
        </div>
      </header>

      {/* Filters */}
      <div className="filters">
        <div className="chips">
          {TYPES.map((t) => (
            <button
              key={t}
              className={`chip ${type === t ? "active" : ""}`}
              onClick={() => setType(t)}
            >
              {t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
        <select
          className="sort"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          aria-label="Sort"
        >
          {SORTS.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      {/* Grid/List */}
      <main className={view === "grid" ? "browse-grid" : "browse-list"}>
        {loading
          ? Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)
          : filtered.length > 0
          ? filtered.map((p) => (
              <div key={p.post_id} className={view === "list" ? "list-card" : ""}>
                <PostCard post={p} />
              </div>
            ))
          : (
            <div className="empty-state">
              <img src="/placeholder.png" alt="" />
              <h3>No posts yet</h3>
              <p>Try different filters, or create the first post in your community.</p>
              <a className="cta" href="/create">Create Post</a>
            </div>
          )}
      </main>

      <BottomNav />
    </div>
  );
}

export default BrowsePage;
