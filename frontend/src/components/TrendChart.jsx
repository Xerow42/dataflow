import React from "react";
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";

export function TemperatureTrendChart({ data, xKey }) {
  return (
    <div className="chart-card">
      <h3>Temperature trend</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} />
          <YAxis unit="°C" />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="avg_temp_c" name="Avg temp (°C)" stroke="#2e5cff" dot={false} />
          <Line type="monotone" dataKey="temp_mean_c" name="Daily mean (°C)" stroke="#2e5cff" dot={false} />
          <Line type="monotone" dataKey="temp_mean_7d_rolling" name="7-day rolling mean" stroke="#ff8a2e" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function PrecipitationChart({ data, xKey }) {
  return (
    <div className="chart-card">
      <h3>Precipitation</h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} />
          <YAxis unit="mm" />
          <Tooltip />
          <Bar dataKey="precipitation_sum_mm" name="Precipitation (mm)" fill="#2ec4ff" />
          <Bar dataKey="precipitation_mm" name="Precipitation (mm)" fill="#2ec4ff" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
