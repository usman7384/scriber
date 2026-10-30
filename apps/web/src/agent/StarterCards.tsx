import { useT } from "../i18n";
import { QuantityText } from "./QuantityText";

const starters = [
  "Mounting plate 100 x 60 x 5 mm with four M5 clearance holes 8 mm from each edge",
  "L-bracket, legs 40 and 30 mm, 4 mm thick, 25 mm wide, two M4 holes per leg",
  "Spacer ring, 30 mm outer diameter, 12 mm bore, 8 mm tall",
  "Electronics box 120 x 80 x 40 mm, 2 mm walls, open top",
];

export function StarterCards({ onPick }: { onPick: (text: string) => void }) {
  const t = useT();
  return (
    <div role="group" aria-label={t.prompt.examples} className="agent-starters">
      {starters.map((text) => (
        <button key={text} type="button" className="agent-starter" onClick={() => onPick(text)}>
          <QuantityText text={text} />
        </button>
      ))}
    </div>
  );
}
