// src/components/BottomNav.jsx
import { useNavigate } from "react-router-dom";
import "./BottomNav.css";

function BottomNav() {
  const navigate = useNavigate();

  return (
    <div className="bottom-nav">
      <button onClick={() => navigate("/")}>🏠 Home</button>
      <button onClick={() => navigate("/create")}>➕ Post</button>
      <button onClick={() => navigate("/search")}>🔍 Search</button>
      <button onClick={() => navigate("/dashboard")}>👤 Profile</button>
    </div>
  );
}

export default BottomNav;
