import { getLoginUrl } from "../services/api";

function LandingPage() {
  return (
    <div style={{ textAlign: "center", marginTop: "80px" }}>
      <h1>CodeCourt</h1>
      <p>Analyze team contribution activity in your GitHub repositories.</p>
      <a href={getLoginUrl()}>
        <button style={{ padding: "10px 20px", fontSize: "16px" }}>
          Login with GitHub
        </button>
      </a>
    </div>
  );
}

export default LandingPage;