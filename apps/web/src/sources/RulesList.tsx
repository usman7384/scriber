import type { Rule } from "../api";
import { useT } from "../i18n";
import { Icon } from "../ui/icons";

const glyph = { error: "fail", warning: "warn" } as const;

export function RulesList({ rules }: { rules: Rule[] }) {
  const t = useT();
  if (rules.length === 0) return <p className="src-empty">{t.context.noRules}</p>;
  return (
    <table className="src-rules" aria-label={t.context.rules}>
      <thead className="sr-only">
        <tr>
          {t.context.ruleColumns.map((c) => (
            <th key={c}>{c}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rules.map((r) => {
          const icon = glyph[r.severity as keyof typeof glyph];
          return (
            <tr key={r.id}>
              <td>{r.text}</td>
              <td className="mono">
                {r.value} {r.unit}
              </td>
              <td>{t.processes[r.process as keyof typeof t.processes] ?? r.process}</td>
              <td>
                <span className="src-status" data-state={icon}>
                  {icon && <Icon name={icon} size={14} />}
                  {t.status[r.severity] ?? r.severity}
                </span>
              </td>
              <td className="mono">{r.source_ref ?? "—"}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
