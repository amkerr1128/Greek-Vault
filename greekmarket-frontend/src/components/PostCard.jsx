// src/components/PostCard.jsx
import { useNavigate } from "react-router-dom";
import "../styles/PostCard.css";

function PostCard({ post }) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/post/${post.post_id}`);
  };

  return (
    <div className="post-card" onClick={handleClick}>
      <img
        src={post.main_image_url || "/placeholder.png"}
        alt={post.title}
        className="post-image"
      />
      <div className="post-meta">
        <h3 className="post-title">{post.title}</h3>
        {post.price != null && (
          <p className="post-price">${Number(post.price).toFixed(2)}</p>
        )}
        <p className="post-seller">@{post.user_handle}</p>
      </div>
    </div>
  );
}

export default PostCard;
