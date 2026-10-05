import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import { getRepositoryAnalysis } from "../services/api";

function StatCard({ label, value }) {
  return (
    <div
      style={{
        border: "1px solid #ccc",
        padding: "16px",
        textAlign: "center",
        minWidth: "140px",
      }}
    >
      <div
        style={{
          fontSize: "13px",
          color: "#666",
        }}
      >
        {label}
      </div>

      <div
        style={{
          fontSize: "28px",
          fontWeight: "bold",
        }}
      >
        {value}
      </div>
    </div>
  );
}

function DashboardPage() {
  const { repositoryId } = useParams();

  const [data, setData] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    getRepositoryAnalysis(repositoryId)
      .then((result) => {
        setData(result);
        setStatus("success");
      })
      .catch((err) => {
        if (err.response && err.response.status === 401) {
          window.location.href = "/login";
        } else {
          setStatus("error");
        }
      });
  }, [repositoryId]);

  if (status === "loading") {
    return <p>Loading analysis...</p>;
  }

  if (status === "error") {
    return <p>Unable to load analysis. Please try again.</p>;
  }

  const { repository, summary, contributors, activity } = data;

  return (
    <div style={{ padding: "40px" }}>
      <h2>{repository.name}</h2>

      <p>
        Owner: {repository.owner} &nbsp;|&nbsp;
        <a
          href={repository.url}
          target="_blank"
          rel="noreferrer"
        >
          View on GitHub
        </a>
      </p>

      {/* Statistics */}
      <div
        style={{
          display: "flex",
          gap: "16px",
          margin: "20px 0",
        }}
      >
        <StatCard
          label="Contributors"
          value={summary.total_contributors}
        />

        <StatCard
          label="Commits"
          value={summary.total_commits}
        />

        <StatCard
          label="Additions"
          value={summary.total_additions}
        />

        <StatCard
          label="Deletions"
          value={summary.total_deletions}
        />
      </div>

      {/* Contributors */}
      <h3>Contributors</h3>

      <table
        style={{
          borderCollapse: "collapse",
          width: "100%",
          marginBottom: "30px",
        }}
      >
        <thead>
          <tr>
            <th
              style={{
                border: "1px solid #ccc",
                padding: "8px",
              }}
            >
              Contributor
            </th>

            <th
              style={{
                border: "1px solid #ccc",
                padding: "8px",
              }}
            >
              Commits
            </th>

            <th
              style={{
                border: "1px solid #ccc",
                padding: "8px",
              }}
            >
              Additions
            </th>

            <th
              style={{
                border: "1px solid #ccc",
                padding: "8px",
              }}
            >
              Deletions
            </th>

            <th
              style={{
                border: "1px solid #ccc",
                padding: "8px",
              }}
            >
              Files
            </th>
          </tr>
        </thead>

        <tbody>
          {contributors.map((c) => (
            <tr key={c.username}>
              <td
                style={{
                  border: "1px solid #ccc",
                  padding: "8px",
                }}
              >
                {c.username}
              </td>

              <td
                style={{
                  border: "1px solid #ccc",
                  padding: "8px",
                }}
              >
                {c.commits}
              </td>

              <td
                style={{
                  border: "1px solid #ccc",
                  padding: "8px",
                }}
              >
                {c.additions}
              </td>

              <td
                style={{
                  border: "1px solid #ccc",
                  padding: "8px",
                }}
              >
                {c.deletions}
              </td>

              <td
                style={{
                  border: "1px solid #ccc",
                  padding: "8px",
                }}
              >
                {c.files_changed}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Commit Activity */}
      <h3>Commit activity</h3>

      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={activity}>
          <CartesianGrid strokeDasharray="3 3" />

          <XAxis dataKey="date" />

          <YAxis allowDecimals={false} />

          <Tooltip />

          <Line
            type="monotone"
            dataKey="commits"
            stroke="#8884d8"
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Contributor Comparison */}
      <h3>Contributor comparison</h3>

      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={contributors}>
          <CartesianGrid strokeDasharray="3 3" />

          <XAxis dataKey="username" />

          <YAxis allowDecimals={false} />

          <Tooltip />

          <Bar
            dataKey="commits"
            fill="#82ca9d"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default DashboardPage;