export function Kbd({ keys }: { keys: string[] }) {
  return (
    <span className="ui-kbd">
      {keys.map((key) => (
        <kbd key={key}>{key}</kbd>
      ))}
    </span>
  );
}
