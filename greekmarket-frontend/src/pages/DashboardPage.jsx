// src/pages/DashboardPage.jsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/axios";
import "./DashboardPage.css";

function DashboardPage() {
  const [userData, setUserData] = useState(null);
  const [posts, setPosts] = useState([]);
  const [showMenu, setShowMenu] = useState(false);
  const navigate = useNavigate();

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem("token");
      const config = { headers: { Authorization: `Bearer ${token}` } };

      const userRes = await api.get("/me", config);
      setUserData(userRes.data);

      const postRes = await api.get("/my-posts", config);
      setPosts(postRes.data);
    } catch (err) {
      console.error("Error loading dashboard:", err);
      navigate("/login");
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleAccountSetup = async () => {
    try {
      const token = localStorage.getItem("token");
      const config = { headers: { Authorization: `Bearer ${token}` } };
      const res = await api.post("/create-account-link", {}, config);
      window.location.href = res.data.url;
    } catch (err) {
      console.error("Error setting up Stripe account:", err);
      alert("Failed to initiate Stripe onboarding.");
    }
  };

  if (!userData) return <p>Loading...</p>;

  return (
    <div className="dashboard">
      <div className="header">
        <div>
          <h2>{userData.first_name} {userData.last_name}</h2>
          <p>@{userData.handle}</p>
          <p>{userData.chapter_name}</p>
        </div>
        <img
          src={userData.profile_picture_url || "/default-profile.png"}
          alt="Profile"
          className="profile-pic"
        />
        <div className="menu-icon" onClick={() => setShowMenu(!showMenu)}>
          &#9776;
        </div>
      </div>

      {showMenu && (
        <div className="dropdown-menu">
          <button onClick={() => navigate("/purchases")}>My Purchases</button>
          <button onClick={() => navigate("/edit-profile")}>Edit Profile</button>
        </div>
      )}

      <div className="dashboard-buttons">
        <button onClick={() => navigate("/create-post")}>Create Post</button>
        {!userData.stripe_account_id && (
          <button onClick={handleAccountSetup} className="setup-btn">
            Complete Account Setup
          </button>
        )}
      </div>

      <h3>Recent Posts</h3>
      <div className="post-grid">
        {posts.length === 0 ? (
          <p>No posts yet.</p>
        ) : (
          posts.map((post) => (
            <div key={post.post_id} className="post-card">
              <img src={post.image_url || "/placeholder.png"} alt="Post" />
              <p>{post.title}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default DashboardPage;
