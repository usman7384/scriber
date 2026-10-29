import { useState, type FormEvent } from "react";
import type { FaceDriver, Param } from "../api";

interface Props {
  driver: FaceDriver;
  params: Param[];
  busy: boolean;
  onApply: (values: Record<string, number>) => void;
  onClose: () => void;
}

export function FaceEdit({ driver, params, busy, onApply, onClose }: Props) {
  const [offset, setOffset] = useState("");
  const param = params.find((p) => p.name === driver.param);
  if (!param) return null;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    onApply({ [param.name]: +(param.value + Number(offset) / driver.rate).toFixed(6) });
  };
  return (
    <form className="panel row wrap" aria-label="Face edit" onSubmit={submit}>
      <span>
        Face of <strong>{driver.part}</strong> is driven by <strong>{param.label}</strong> ({param.value}{" "}
        {param.unit})
      </span>
      <label className="row">
        Offset (mm)
        <input type="number" step="any" value={offset} onChange={(e) => setOffset(e.target.value)} required />
      </label>
      <button type="submit" className="primary" disabled={busy || offset === ""}>
        Apply
      </button>
      <button type="button" className="secondary" onClick={onClose}>
        Close
      </button>
    </form>
  );
}
