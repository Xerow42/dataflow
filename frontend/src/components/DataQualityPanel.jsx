import React from "react";

export default function DataQualityPanel({ runs }) {
  if (!runs || runs.length === 0) return null;
  return (
    <div className="dq-panel">
      <h3>Data quality — recent pipeline runs</h3>
      <table>
        <thead>
          <tr>
            <th>Run started</th><th>Processed</th><th>Valid</th>
            <th>Duplicates removed</th><th>Invalid</th><th>Outliers</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r, i) => (
            <tr key={i}>
              <td>{r.run_started_at}</td>
              <td>{r.records_processed}</td>
              <td>{r.valid_records}</td>
              <td>{r.duplicates_removed}</td>
              <td>{r.invalid_records}</td>
              <td>{r.outliers_flagged}</td>
              <td className={r.status === "success" ? "status-ok" : "status-failed"}>{r.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
