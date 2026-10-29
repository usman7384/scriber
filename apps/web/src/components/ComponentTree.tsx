import type { Component } from "../api";

interface Props {
  components: Component[];
  selected?: string | undefined;
  onSelect: (id: string | undefined) => void;
}

export function ComponentTree({ components, selected, onSelect }: Props) {
  const branch = (parent: string | null, label?: string) => (
    <ul className="tree" aria-label={label}>
      {components
        .filter((c) => c.parent === parent)
        .map((c) => (
          <li key={c.id}>
            <button
              type="button"
              aria-pressed={c.id === selected}
              data-id={c.id}
              title={c.joint ?? undefined}
              onClick={() => onSelect(c.id === selected ? undefined : c.id)}
            >
              {c.name} <span className="muted small">{c.id}</span>
            </button>
            {components.some((k) => k.parent === c.id) && branch(c.id)}
          </li>
        ))}
    </ul>
  );
  return branch(null, "Components");
}
