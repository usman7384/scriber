import type { Param, Version } from "./api";

type Listener = (e: MessageEvent<string>) => void;

export class FakeEventSource {
  static readonly CLOSED = 2;
  static instances: FakeEventSource[] = [];
  readyState = 1;
  onerror: (() => void) | null = null;
  private listeners = new Map<string, Listener[]>();

  constructor(readonly url: string) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, fn: Listener) {
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), fn]);
  }

  close() {
    this.readyState = FakeEventSource.CLOSED;
  }

  emit(type: string, data: unknown) {
    const e = new MessageEvent(type, { data: JSON.stringify(data) });
    this.listeners.get(type)?.forEach((fn) => fn(e));
  }
}

export const param = (over: Partial<Param> = {}): Param => ({
  name: "plate_length",
  label: "Plate Length",
  value: 120,
  unit: "mm",
  description: "plate length",
  provenance: { source: "document", ref: "spec.pdf#p1:l2", quote: "Plate size 120 x 80 x 6 mm" },
  ...over,
});

export const version = (number: number, over: Partial<Version> = {}): Version => ({
  model_id: "m1",
  number,
  created: `2026-10-26T10:0${number}:00Z`,
  status: "ok",
  origin: number === 1 ? "generate" : "params",
  prompt: number === 1 ? "Sensor plate" : null,
  params: [param()],
  checks: [],
  findings: [],
  metrics: { bbox: [120, 80, 6], volume: 54000, holes: 4 },
  files: { step: "", stl: "", glb: "", py: "", ir: "" },
  thumbnail_url: null,
  ...over,
});
