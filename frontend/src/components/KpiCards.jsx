import React from "react";

export default function KpiCards({ metrics }) {
  if (!metrics) return null;
  return (
    <div className="kpi-grid">
      <div className="kpi-card">
        <div className="label">Records</div>
        <div className="value">{metrics.records}</div>
      </div>
      <div className="kpi-card">
        <div className="label">Avg. temperature</div>
        <div className="value">{metrics.avg_temp_c}°C</div>
      </div>
      <div className="kpi-card">
        <div className="label">Total precipitation</div>
        <div className="value">{metrics.total_precipitation_mm} mm</div>
      </div>
      <div className="kpi-card">
        <div className="label">Hottest day</div>
        <div className="value">{metrics.hottest_day?.temp_max_c}°C</div>
        <div className="label">{metrics.hottest_day?.date}</div>
      </div>
      <div className="kpi-card">
        <div className="label">Coldest day</div>
        <div className="value">{metrics.coldest_day?.temp_min_c}°C</div>
        <div className="label">{metrics.coldest_day?.date}</div>
      </div>
    </div>
  );
}
