import type { Rule } from "../api";

export function RulesTable({ rules }: { rules: Rule[] }) {
  if (rules.length === 0) return <p className="muted">No project rules yet.</p>;
  return (
    <div className="table-wrap">
      <table aria-label="Project rules">
        <thead>
          <tr>
            <th>Rule</th>
            <th>Limit</th>
            <th>Process</th>
            <th>Severity</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody>
          {rules.map((r) => (
            <tr key={r.id}>
              <td>{r.text}</td>
              <td>
                {r.value} {r.unit}
              </td>
              <td>{r.process}</td>
              <td>
                <span className={`badge ${r.severity}`}>{r.severity}</span>
              </td>
              <td className="muted small">{r.source_ref ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
