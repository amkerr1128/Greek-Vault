// src/utils/logout.js
import API from "../api/axios";

export default async function logout() {
  try {
    await API.post("/logout");
  } catch (err) {
    console.error("Logout failed:", err);
  }
  localStorage.removeItem("token");
  window.location.href = "/login";
}
