import { useEffect } from "react";

import { getLoginUrl } from "../services/api";

function LoginPage() {
  useEffect(() => {
    window.location.replace(getLoginUrl());
  }, []);

  return <p>Redirecting to GitHub...</p>;
}

export default LoginPage;