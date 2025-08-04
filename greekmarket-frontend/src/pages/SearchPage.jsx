import { useState } from "react";
import "../styles/SearchPage.css";

function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState({ users: [], schools: [], chapters: [] });

  const handleSearch = async (e) => {
    e.preventDefault();

    if (!query.trim()) return;

    try {
      const res = await fetch(`http://localhost:5000/search?q=${encodeURIComponent(query)}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });
      const data = await res.json();
      setResults(data);
    } catch (err) {
      console.error("Search failed:", err);
    }
  };

  return (
    <div className="search-page">
      <h2>Search</h2>
      <form onSubmit={handleSearch} className="search-form">
        <input
          type="text"
          placeholder="Search for users, schools, or chapters..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit">Search</button>
      </form>

      <div className="search-results">
        <div>
          <h3>Users</h3>
          {results.users.map((user) => (
            <p key={user.user_id}>{user.first_name} {user.last_name} (@{user.username})</p>
          ))}
        </div>

        <div>
          <h3>Schools</h3>
          {results.schools.map((school) => (
            <p key={school.school_id}>{school.name}</p>
          ))}
        </div>

        <div>
          <h3>Chapters</h3>
          {results.chapters.map((chapter) => (
            <p key={chapter.chapter_id}>{chapter.name}</p>
          ))}
        </div>
      </div>
    </div>
  );
}

export default SearchPage;
