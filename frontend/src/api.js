import axios from "axios";

// Same-origin API requests work both behind nginx in Docker and through
// Vite's development proxy. An explicit URL is optional for custom hosting.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

const client = axios.create({ baseURL: API_BASE_URL });

export const api = {
  getCategories: () => client.get("/api/categories").then((r) => r.data),
  getMetrics: (city, start, end) =>
    client.get("/api/metrics", { params: { city, start, end } }).then((r) => r.data),
  getTrends: (city, start, end, granularity) =>
    client.get("/api/trends", { params: { city, start, end, granularity } }).then((r) => r.data),
  getDataQuality: () => client.get("/api/data-quality").then((r) => r.data),
};
