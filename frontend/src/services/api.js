import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

export function getRepositories() {
  return api.get("/api/repositories").then((response) => response.data);
}

export function getRepositoryAnalysis(repositoryId) {
  return api
    .get(`/api/repositories/${repositoryId}/analysis`)
    .then((response) => response.data);
}

export function getLoginUrl() {
  return `${API_BASE_URL}/auth/github/login`;
}

export default api;