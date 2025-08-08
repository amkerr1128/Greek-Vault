// src/pages/SignUpPage.jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../api/axios";

function SignUpPage() {
  const [schools, setSchools] = useState([]);
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    handle: "",
    email: "",
    password: "",
    school_id: "",
  });
  const [errorMsg, setErrorMsg] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      try {
        const { data } = await API.get("/schools");
        setSchools(data);
        if (data.length && !form.school_id) {
          setForm((f) => ({ ...f, school_id: data[0].id }));
        }
      } catch (e) {
        console.error("Failed to load schools", e);
      }
    })();
  }, []);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    try {
      await API.post("/register", {
        first_name: form.first_name,
        last_name: form.last_name,
        handle: form.handle,
        email: form.email,
        password: form.password,
        school_id: Number(form.school_id),
      });
      // backend doesn't return a token on register -> login now
      const { data } = await API.post("/login", { email: form.email, password: form.password });
      localStorage.setItem("token", data.access_token);
      navigate("/browse");
    } catch (err) {
      setErrorMsg(err.response?.data?.error || "Signup failed. Try a different email/handle.");
    }
  };

  return (
    <div style={styles.container}>
      <h2>Create a GreekVault Account</h2>
      <form onSubmit={onSubmit} style={styles.form}>
        <input name="first_name" placeholder="First Name" required value={form.first_name} onChange={onChange} style={styles.input} />
        <input name="last_name"  placeholder="Last Name"  required value={form.last_name}  onChange={onChange} style={styles.input} />
        <input name="handle"     placeholder="Handle (username)" required value={form.handle} onChange={onChange} style={styles.input} />
        <input type="email" name="email" placeholder="Email" required value={form.email} onChange={onChange} style={styles.input} />
        <input type="password" name="password" placeholder="Password" required value={form.password} onChange={onChange} style={styles.input} />
        <select name="school_id" value={form.school_id} onChange={onChange} style={styles.input}>
          {schools.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <button type="submit" style={styles.button}>Sign Up</button>
      </form>
      {errorMsg && <p style={styles.error}>{errorMsg}</p>}
      <p>Already have an account? <button onClick={() => navigate("/login")} style={styles.link}>Log In</button></p>
    </div>
  );
}

const styles = {
  container: { maxWidth: 420, margin: "auto", padding: 20, textAlign: "center" },
  form: { display: "flex", flexDirection: "column", gap: 10 },
  input: { padding: 10, fontSize: 16 },
  button: { padding: 10, fontSize: 16, backgroundColor: "#111", color: "white", border: "none", cursor: "pointer" },
  error: { color: "red", marginTop: 10 },
  link: { background: "none", border: "none", color: "#007bff", textDecoration: "underline", cursor: "pointer" },
};

export default SignUpPage;
