import type { Rule } from "../api";
import { useT } from "../i18n";

export function RulesTable({ rules }: { rules: Rule[] }) {
  const t = useT();
  if (rules.length === 0) return <p className="muted">{t.context.noRules}</p>;
  return (
    <div className="table-wrap">
      <table aria-label={t.context.rules}>
        <thead>
          <tr>
            {t.context.ruleColumns.map((c) => (
              <th key={c}>{c}</th>
            ))}
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
                <span className={`badge ${r.severity}`}>{t.status[r.severity] ?? r.severity}</span>
              </td>
              <td className="muted small">{r.source_ref ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
