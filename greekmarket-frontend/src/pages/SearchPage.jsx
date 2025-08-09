import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import API from "../api/axios";
import "../styles/SearchPage.css";

/** Spelled-out greek -> Greek letters */
const GREEK_MAP = {
  alpha: "Α",
  beta: "Β",
  gamma: "Γ",
  delta: "Δ",
  epsilon: "Ε",
  zeta: "Ζ",
  eta: "Η",
  theta: "Θ",
  iota: "Ι",
  kappa: "Κ",
  lambda: "Λ",
  lamda: "Λ",
  mu: "Μ",
  nu: "Ν",
  xi: "Ξ",
  omicron: "Ο",
  pi: "Π",
  rho: "Ρ",
  sigma: "Σ",
  tau: "Τ",
  upsilon: "Υ",
  phi: "Φ",
  chi: "Χ",
  psi: "Ψ",
  omega: "Ω",
};

function chapterGreekMonogram(name) {
  if (!name) return "";
  const base = name.replace(/\(.*?\)/g, "").toLowerCase();
  const tokens = base
    .split(/[^a-z]+/i)
    .filter(Boolean)
    .map((t) => t.toLowerCase());

  const letters = [];
  for (const t of tokens) {
    if (GREEK_MAP[t]) {
      letters.push(GREEK_MAP[t]);
      if (letters.length === 3) break;
    }
  }
  if (letters.length === 0) {
    const lat = base
      .split(/\s+/)
      .filter(Boolean)
      .map((w) => w[0]?.toUpperCase())
      .slice(0, 3);
    return lat.join("");
  }
  return letters.join("");
}

function schoolAcronym(name) {
  if (!name) return "";
  return name
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .filter(Boolean)
    .map((w) => w[0]?.toUpperCase())
    .slice(0, 3)
    .join("");
}

function userInitials(first, last, handle) {
  const a = (first || "").trim();
  const b = (last || "").trim();
  if (a || b) {
    return `${a?.[0] || ""}${b?.[0] || ""}`.toUpperCase() || (handle?.[0] || "?").toUpperCase();
  }
  return (handle?.slice(0, 2) || "U").toUpperCase();
}

export default function SearchPage() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") || "");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const nav = useNavigate();
  const debounceRef = useRef(null);

  // Merge three endpoints into a single list
  const doSearch = async (query) => {
    if (!query?.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const [u, s, c] = await Promise.all([
        API.get(`/search/users?q=${encodeURIComponent(query)}`).catch(() => ({ data: [] })),
        API.get(`/search/schools?q=${encodeURIComponent(query)}`).catch(() => ({ data: [] })),
        API.get(`/search/chapters?q=${encodeURIComponent(query)}`).catch(() => ({ data: [] })),
      ]);

      const users = (u.data || []).map((x) => ({
        _type: "user",
        id: x.user_id,
        title: `${x.first_name || ""} ${x.last_name || ""}`.trim() || x.handle,
        subtitle: x.email || `@${x.handle}`,
        avatar: userInitials(x.first_name, x.last_name, x.handle),
        href: `/user/${x.user_id}`,
      }));

      const schools = (s.data || []).map((x) => ({
        _type: "school",
        id: x.school_id,
        title: x.name,
        subtitle: x.domain,
        avatar: schoolAcronym(x.name),
        href: `/school/${x.school_id}`,
      }));

      const chapters = (c.data || []).map((x) => ({
        _type: "chapter",
        id: x.chapter_id,
        title: x.name,
        subtitle: x.type,
        avatar: chapterGreekMonogram(x.name),
        verified: !!x.verified,
        href: `/chapter/${x.chapter_id}`,
      }));

      // Simple relevance-ish ordering: chapters first (usually what people want), then schools, then users.
      const merged = [...chapters, ...schools, ...users];
      setResults(merged);
    } finally {
      setLoading(false);
    }
  };

  // kick off on mount if there's a query in the URL
  useEffect(() => {
    if (q.trim()) doSearch(q);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // live (debounced) search on input change + keep ?q= in the URL
  useEffect(() => {
    params.set("q", q);
    setParams(params, { replace: true });

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(q), 300);
    return () => clearTimeout(debounceRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  const countLabel = useMemo(() => {
    if (loading) return "Searching…";
    if (!q.trim()) return "";
    const n = results.length;
    return n === 1 ? "1 result" : `${n} results`;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [results, loading]);

  return (
    <div className="search-page">
      <header className="search-head">
        <h1>Search</h1>
        <form
          className="searchbar"
          onSubmit={(e) => {
            e.preventDefault();
            doSearch(q);
          }}
        >
          <span className="icon">🔎</span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search users, schools, chapters…"
            aria-label="Search"
          />
          <button className="btn" type="submit">
            Search
          </button>
        </form>
        {!!countLabel && <div className="count">{countLabel}</div>}
      </header>

      <main className="result-list">
        {loading && results.length === 0 && (
          <>
            {Array.from({ length: 5 }).map((_, i) => (
              <div className="result-card skeleton" key={i}>
                <div className="avatar shimmer" />
                <div className="meta">
                  <div className="line shimmer" />
                  <div className="sub shimmer" />
                </div>
              </div>
            ))}
          </>
        )}

        {!loading && results.length === 0 && q.trim() && (
          <div className="empty">No matches. Try a different query.</div>
        )}

        {results.map((r) => (
          <button
            key={`${r._type}:${r.id}`}
            className="result-card"
            onClick={() => nav(r.href)}
          >
            <div className={`avatar ${r._type}`}>
              <span>{r.avatar || "?"}</span>
            </div>
            <div className="meta">
              <div className="title-row">
                <div className="title">{r.title}</div>
                {r._type === "chapter" && <span className="pill">Chapter</span>}
                {r._type === "school" && <span className="pill neutral">School</span>}
                {r._type === "user" && <span className="pill neutral">User</span>}
                {r.verified && <span className="pill ok">Verified</span>}
              </div>
              <div className="sub">{r.subtitle}</div>
            </div>
            <div className="chev">›</div>
          </button>
        ))}
      </main>
    </div>
  );
}
