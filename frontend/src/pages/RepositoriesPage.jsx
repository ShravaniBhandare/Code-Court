import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getRepositories } from "../services/api";

function RepositoriesPage() {
  const [repos, setRepos] = useState([]);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    getRepositories()
      .then((data) => {
        setRepos(data.repositories);
        setStatus("success");
      })
      .catch((err) => {
        if (err.response && err.response.status === 401) {
          window.location.href = "/login";
        } else {
          setStatus("error");
        }
      });
  }, []);

  if (status === "loading") return <p>Loading repositories...</p>;
  if (status === "error") return <p>Unable to load repositories. Please try again.</p>;
  if (repos.length === 0) return <p>No repositories available.</p>;

  return (
    <div style={{ padding: "40px" }}>
      <h2>Your repositories</h2>
      {repos.map((repo) => (
        <div
          key={repo.id}
          style={{ border: "1px solid #ccc", padding: "16px", marginBottom: "12px" }}
        >
          <strong>{repo.name}</strong> <span>({repo.owner})</span>
          <div>
            <Link to={`/dashboard/${repo.id}`}>
              <button style={{ marginTop: "8px" }}>Analyze</button>
            </Link>
          </div>
        </div>
      ))}
    </div>
  );
}

export default RepositoriesPage;