import React, { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import Filters from "./components/Filters";
import KpiCards from "./components/KpiCards";
import { TemperatureTrendChart, PrecipitationChart } from "./components/TrendChart";
import DataQualityPanel from "./components/DataQualityPanel";

function defaultDates() {
  const end = new Date();
  const start = new Date();
  start.setFullYear(start.getFullYear() - 1);
  const fmt = (d) => d.toISOString().slice(0, 10);
  return { start: fmt(start), end: fmt(end) };
}

export default function App() {
  const { start: defaultStart, end: defaultEnd } = defaultDates();

  const [cities, setCities] = useState([]);
  const [city, setCity] = useState("Lille");
  const [start, setStart] = useState(defaultStart);
  const [end, setEnd] = useState(defaultEnd);
  const [granularity, setGranularity] = useState("monthly");

  const [metrics, setMetrics] = useState(null);
  const [trends, setTrends] = useState([]);
  const [dataQuality, setDataQuality] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getCategories().then(setCities).catch(() => setCities([{ city_name: "Lille" }]));
    api.getDataQuality().then(setDataQuality).catch(() => setDataQuality([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      api.getMetrics(city, start, end),
      api.getTrends(city, start, end, granularity),
    ])
      .then(([m, t]) => {
        if (cancelled) return;
        setMetrics(m);
        setTrends(t);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.response?.data?.detail || "Could not load data for this selection.");
        setMetrics(null);
        setTrends([]);
      })
      .finally(() => !cancelled && setLoading(false));

    return () => { cancelled = true; };
  }, [city, start, end, granularity]);

  const xKey = granularity === "daily" ? "observation_date" : "period";

  const trendsForChart = useMemo(
    () => trends.map((row) => ({
      ...row,
      observation_date: row.observation_date ? String(row.observation_date).slice(0, 10) : undefined,
    })),
    [trends]
  );

  return (
    <div className="app">
      <div className="header">
        <h1>🌦️ DataFlow — Weather &amp; Climate Analytics</h1>
        <span>Data source: Open-Meteo</span>
      </div>

      <Filters
        cities={cities.length ? cities : [{ city_name: "Lille" }]}
        city={city} setCity={setCity}
        start={start} setStart={setStart}
        end={end} setEnd={setEnd}
        granularity={granularity} setGranularity={setGranularity}
      />

      {error && <div className="error-banner">{error}</div>}
      {loading && <p>Loading…</p>}

      <KpiCards metrics={metrics} />
      <TemperatureTrendChart data={trendsForChart} xKey={xKey} />
      <PrecipitationChart data={trendsForChart} xKey={xKey} />
      <DataQualityPanel runs={dataQuality} />
    </div>
  );
}
