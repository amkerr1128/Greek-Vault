// src/pages/LoginPage.jsx
import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import API from "../api/axios";
import "../styles/LoginPage.css";

export default function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const { data } = await API.post("/login", { email, password });
      // Save short-lived access token (refresh cookie is HttpOnly & automatic)
      localStorage.setItem("token", data.access_token);
      navigate("/browse");
    } catch (err) {
      const msg =
        err?.response?.data?.error ||
        "Login failed. Please check your email and password.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-container">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h2>Login to GreekVault</h2>

        <input
          type="email"
          placeholder="Email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <input
          type="password"
          placeholder="Password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <button type="submit" disabled={submitting}>
          {submitting ? "Logging in…" : "Log In"}
        </button>

        {error && <div className="error">{error}</div>}

        <div className="links">
          <button
            type="button"
            onClick={() => alert("Forgot password flow coming soon")}
          >
            Forgot Password?
          </button>
          <Link to="/signup">Sign Up</Link>
        </div>
      </form>
    </div>
  );
}
