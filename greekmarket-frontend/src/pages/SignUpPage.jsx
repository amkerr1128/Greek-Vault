// src/pages/SignUpPage.jsx
import { useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

function SignUpPage() {
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    handle: "",
    email: "",
    password: "",
  });
  const [errorMsg, setErrorMsg] = useState("");

  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    setErrorMsg("");

    try {
      const res = await axios.post("http://localhost:5000/signup", formData);
      if (res.data.access_token) {
        localStorage.setItem("token", res.data.access_token);
        navigate("/"); // Redirect to dashboard after signup
      }
    } catch (err) {
      setErrorMsg(
        err.response?.data?.msg || "Signup failed. Try a different email or handle."
      );
    }
  };

  return (
    <div style={styles.container}>
      <h2>Create a GreekMarket Account</h2>
      <form onSubmit={handleSignUp} style={styles.form}>
        <input
          type="text"
          name="first_name"
          placeholder="First Name"
          required
          value={formData.first_name}
          onChange={handleChange}
          style={styles.input}
        />
        <input
          type="text"
          name="last_name"
          placeholder="Last Name"
          required
          value={formData.last_name}
          onChange={handleChange}
          style={styles.input}
        />
        <input
          type="text"
          name="handle"
          placeholder="Handle (username)"
          required
          value={formData.handle}
          onChange={handleChange}
          style={styles.input}
        />
        <input
          type="email"
          name="email"
          placeholder="Email"
          required
          value={formData.email}
          onChange={handleChange}
          style={styles.input}
        />
        <input
          type="password"
          name="password"
          placeholder="Password"
          required
          value={formData.password}
          onChange={handleChange}
          style={styles.input}
        />
        <button type="submit" style={styles.button}>
          Sign Up
        </button>
      </form>
      {errorMsg && <p style={styles.error}>{errorMsg}</p>}
      <p>
        Already have an account?{" "}
        <button onClick={() => navigate("/login")} style={styles.link}>
          Log In
        </button>
      </p>
    </div>
  );
}

const styles = {
  container: {
    maxWidth: 400,
    margin: "auto",
    padding: 20,
    textAlign: "center",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  input: {
    padding: 10,
    fontSize: 16,
  },
  button: {
    padding: 10,
    fontSize: 16,
    backgroundColor: "#28a745",
    color: "white",
    border: "none",
    cursor: "pointer",
  },
  error: {
    color: "red",
    marginTop: 10,
  },
  link: {
    background: "none",
    border: "none",
    color: "#007bff",
    textDecoration: "underline",
    cursor: "pointer",
  },
};

export default SignUpPage;
