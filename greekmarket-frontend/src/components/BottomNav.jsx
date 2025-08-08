import { Link, useLocation } from "react-router-dom";
import "../styles/bottomnav.css";

function BottomNav() {
  const location = useLocation();

  return (
    <nav className="bottom-nav">
      <Link
        to="/browse"
        className={`nav-item ${location.pathname === "/browse" ? "active" : ""}`}
      >
        <span role="img" aria-label="home">🏠</span>
        <span>Home</span>
      </Link>

      <Link
        to="/create"  // <-- corrected
        className={`nav-item ${location.pathname === "/create" ? "active" : ""}`}
      >
        <span role="img" aria-label="post">➕</span>
        <span>Post</span>
      </Link>

      <Link
        to="/search"
        className={`nav-item ${location.pathname === "/search" ? "active" : ""}`}
      >
        <span role="img" aria-label="search">🔍</span>
        <span>Search</span>
      </Link>

      <Link
        to="/dashboard"
        className={`nav-item ${location.pathname === "/dashboard" ? "active" : ""}`}
      >
        <span role="img" aria-label="profile">👤</span>
        <span>Profile</span>
      </Link>
    </nav>
  );
}

export default BottomNav;
