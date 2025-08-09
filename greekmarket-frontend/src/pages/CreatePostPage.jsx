// src/pages/CreatePostPage.jsx
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import API from "../api/axios";
import "../styles/CreatePostPage.css";

const TYPES = ["apparel", "accessories", "stickers", "tickets", "other"];

export default function CreatePostPage() {
  const navigate = useNavigate();

  // Auth + gating
  const [me, setMe] = useState(null);
  const [loadingMe, setLoadingMe] = useState(true);

  // Form
  const [type, setType] = useState("apparel");
  const [title, setTitle] = useState("");
  const [price, setPrice] = useState("");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState([]);
  const [visibility] = useState("public"); // future: allow "school" / "chapter"

  // UX
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [okMsg, setOkMsg] = useState("");

  const canSubmit = useMemo(() => {
    if (!title.trim()) return false;
    if (!type) return false;
    if (price && isNaN(Number(price))) return false;
    return true;
  }, [title, type, price]);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await API.get("/me");
        setMe(data);
      } catch (e) {
        if (e?.response?.status === 401) {
          localStorage.removeItem("token");
          navigate("/login");
          return;
        }
        setMe(null);
      } finally {
        setLoadingMe(false);
      }
    })();
  }, [navigate]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setOkMsg("");

    if (!me?.school_id) {
      setError("Please select your school before creating a post.");
      return;
    }
    if (!canSubmit) {
      setError("Please complete the required fields.");
      return;
    }

    setSubmitting(true);
    try {
      // 1) Upload images (optional)
      let image_urls = [];
      if (files && files.length > 0) {
        const uploads = [];
        for (const f of files) {
          const fd = new FormData();
          fd.append("image", f);
          uploads.push(
            API.post("/upload-image", fd, {
              headers: { "Content-Type": "multipart/form-data" },
            }).then((res) => res.data?.url)
          );
        }
        image_urls = (await Promise.all(uploads)).filter(Boolean);
      }

      // 2) Create the post
      const payload = {
        type,
        title: title.trim(),
        description: description.trim() || null,
        price: price ? Number(price) : null,
        visibility,
        image_urls,
      };

      const { data } = await API.post("/posts", payload);
      setOkMsg("Post created!");
      setTimeout(() => navigate(`/post/${data.post_id ?? ""}` || "/browse"), 400);

      // reset form
      setTitle("");
      setPrice("");
      setDescription("");
      setFiles([]);
    } catch (err) {
      const status = err?.response?.status;
      const msg =
        err?.response?.data?.error ||
        err?.message ||
        `Request failed${status ? ` (HTTP ${status})` : ""}`;
      setError(msg);
      // eslint-disable-next-line no-console
      console.error("Create post error:", err, err?.response?.data);
    } finally {
      setSubmitting(false);
    }
  }

  // Loading / gating UI
  if (loadingMe) {
    return (
      <div className="create-post-wrap">
        <div className="create-card">
          <h2 className="create-title">Create a New Post</h2>
          <p className="muted">Loading…</p>
        </div>
      </div>
    );
  }

  if (!me?.school_id) {
    return (
      <div className="create-post-wrap">
        <div className="create-card">
          <h2 className="create-title">Create a New Post</h2>
          <div className="gate-card">
            <h3>Join a school to start posting</h3>
            <p className="muted">
              You’ll need to join your school’s community before you can create posts.
              Search for your school, open its page, and tap <b>Join</b>.
            </p>
            <div className="gate-actions">
              <Link to="/search?q=" className="btn primary">
                Find my school →
              </Link>
              <Link to="/browse" className="btn">
                Browse posts
              </Link>
            </div>
          </div>

          {error && <div className="error mt">{error}</div>}
        </div>
      </div>
    );
  }

  // Main form
  return (
    <div className="create-post-wrap">
      <form className="create-card" onSubmit={handleSubmit}>
        <h2 className="create-title">Create a New Post</h2>

        <label className="field">
          <span>Category</span>
          <select value={type} onChange={(e) => setType(e.target.value)}>
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {t[0].toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Title</span>
          <input
            type="text"
            placeholder="What are you selling?"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </label>

        <label className="field">
          <span>Price (USD)</span>
          <input
            type="text"
            inputMode="decimal"
            placeholder="e.g., 25"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
        </label>

        <label className="field">
          <span>Description (optional)</span>
          <textarea
            rows={4}
            placeholder="Add details, condition, sizing, etc."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>

        <label className="field">
          <span>Photos (optional)</span>
          <input
            type="file"
            multiple
            accept="image/*"
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
          />
          {files?.length > 0 && (
            <div className="muted small mt">{files.length} file(s) selected</div>
          )}
        </label>

        <button className="btn primary block" type="submit" disabled={!canSubmit || submitting}>
          {submitting ? "Creating…" : "Create Post"}
        </button>

        {error && <div className="error mt">{error}</div>}
        {okMsg && <div className="ok mt">{okMsg}</div>}
      </form>
    </div>
  );
}
