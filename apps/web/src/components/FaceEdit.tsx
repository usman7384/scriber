import { useState, type FormEvent } from "react";
import type { FaceDriver, Param } from "../api";
import { useT } from "../i18n";

interface Props {
  driver: FaceDriver;
  params: Param[];
  busy: boolean;
  onApply: (values: Record<string, number>) => void;
  onClose: () => void;
}

export function FaceEdit({ driver, params, busy, onApply, onClose }: Props) {
  const [offset, setOffset] = useState("");
  const t = useT();
  const param = params.find((p) => p.name === driver.param);
  if (!param) return null;
  const submit = (e: FormEvent) => {
    e.preventDefault();
    onApply({ [param.name]: +(param.value + Number(offset) / driver.rate).toFixed(6) });
  };
  return (
    <form className="panel row wrap" aria-label={t.face.form} onSubmit={submit}>
      <span>{t.face.drives(driver.part, param.label, `${param.value} ${param.unit}`)}</span>
      <label className="row">
        {t.face.offset}
        <input type="number" step="any" value={offset} onChange={(e) => setOffset(e.target.value)} required />
      </label>
      <button type="submit" className="primary" disabled={busy || offset === ""}>
        {t.apply}
      </button>
      <button type="button" className="secondary" onClick={onClose}>
        {t.close}
      </button>
    </form>
  );
}
