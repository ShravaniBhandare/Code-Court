import { Route, Routes } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RepositoriesPage from "./pages/RepositoriesPage";
import DashboardPage from "./pages/DashboardPage";

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/repositories" element={<RepositoriesPage />} />
      <Route path="/dashboard/:repositoryId" element={<DashboardPage />} />
    </Routes>
  );
}

export default App;