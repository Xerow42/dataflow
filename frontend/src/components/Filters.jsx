import React from "react";

export default function Filters({ cities, city, setCity, start, setStart, end, setEnd, granularity, setGranularity }) {
  return (
    <div className="filters">
      <select value={city} onChange={(e) => setCity(e.target.value)}>
        {cities.map((c) => (
          <option key={c.city_name} value={c.city_name}>{c.city_name}</option>
        ))}
      </select>
      <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
      <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
      <select value={granularity} onChange={(e) => setGranularity(e.target.value)}>
        <option value="daily">Daily</option>
        <option value="monthly">Monthly</option>
      </select>
    </div>
  );
}
