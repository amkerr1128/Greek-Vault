import { useEffect, useState } from "react";
import axios from "axios";
import "./BrowsePage.css";

function BrowsePage() {
  const [posts, setPosts] = useState([]);

  useEffect(() => {
    const fetchPosts = async () => {
      try {
        const token = localStorage.getItem("token");
        const response = await axios.get("http://localhost:5000/posts", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        setPosts(response.data);
      } catch (error) {
        console.error("Error fetching posts:", error);
      }
    };

    fetchPosts();
  }, []);

  return (
    <div className="browse-container">
      <h2>Browse Posts</h2>
      <div className="browse-grid">
        {posts.map((post) => (
          <div key={post.post_id} className="post-card">
            {post.image_url && (
              <img
                src={post.image_url}
                alt={post.title}
                className="post-image"
              />
            )}
            <h3>{post.title}</h3>
            <p>${post.price}</p>
            <p className="post-seller">@{post.seller_handle}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default BrowsePage;
