// src/components/BottomNav.jsx
import { Link, useLocation } from "react-router-dom";
import "../styles/BottomNav.css";

function BottomNav() {
  const location = useLocation();

  const is = (p) => (location.pathname === p ? "active" : "");

  return (
    <nav className="bottom-nav">
      <Link to="/browse" className={`nav-item ${is("/browse")}`}>
        <span role="img" aria-label="home">🏠</span>
        <span>Home</span>
      </Link>

      <Link to="/create" className={`nav-item ${is("/create")}`}>
        <span role="img" aria-label="post">➕</span>
        <span>Post</span>
      </Link>

      <Link to="/search" className={`nav-item ${is("/search")}`}>
        <span role="img" aria-label="search">🔍</span>
        <span>Search</span>
      </Link>

      <Link to="/dashboard" className={`nav-item ${is("/dashboard")}`}>
        <span role="img" aria-label="profile">👤</span>
        <span>Profile</span>
      </Link>
    </nav>
  );
}

export default BottomNav;
