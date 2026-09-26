import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE_URL });

export const api = {
  getCategories: () => client.get("/api/categories").then((r) => r.data),
  getMetrics: (city, start, end) =>
    client.get("/api/metrics", { params: { city, start, end } }).then((r) => r.data),
  getTrends: (city, start, end, granularity) =>
    client.get("/api/trends", { params: { city, start, end, granularity } }).then((r) => r.data),
  getDataQuality: () => client.get("/api/data-quality").then((r) => r.data),
};
