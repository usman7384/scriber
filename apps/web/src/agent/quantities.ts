export interface Segment {
  text: string;
  quantity: boolean;
}

const num = String.raw`\d+(?:[.,]\d+)?`;
const unit = String.raw`(?:mm|cm|µm|um|m|in|inch|inches|"|°|deg|g|kg|N|Nm|MPa|%)`;
const patterns = [
  String.raw`[Øø⌀]\s*${num}(?:\s*${unit})?`,
  String.raw`\bM${num}(?:\s*[x×]\s*${num})?`,
  String.raw`${num}(?:\s*[x×]\s*${num})+(?:\s*${unit})?`,
  String.raw`(?:±\s*)?${num}\s*${unit}`,
];
// A unit must not run into a word: "4 mounting" is not 4 m.
const quantity = new RegExp(String.raw`(?:${patterns.join("|")})(?![\w])`, "g");

export function splitQuantities(text: string): Segment[] {
  const out: Segment[] = [];
  let at = 0;
  for (const m of text.matchAll(quantity)) {
    const start = m.index;
    if (start > at) out.push({ text: text.slice(at, start), quantity: false });
    out.push({ text: m[0], quantity: true });
    at = start + m[0].length;
  }
  if (at < text.length) out.push({ text: text.slice(at), quantity: false });
  return out;
}
