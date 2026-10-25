interface Props {
  parts: string[];
  selected?: string | undefined;
  onSelect: (part: string | undefined) => void;
}

export function ComponentTree({ parts, selected, onSelect }: Props) {
  return (
    <ul className="tree" aria-label="Components">
      {parts.map((name) => (
        <li key={name}>
          <button
            type="button"
            aria-pressed={name === selected}
            onClick={() => onSelect(name === selected ? undefined : name)}
          >
            {name}
          </button>
        </li>
      ))}
    </ul>
  );
}
