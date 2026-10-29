import { useState, type FormEvent } from "react";
import type { FaceDriver, Param } from "../../api";
import { useT } from "../../i18n";
import { Button } from "../../ui/Button";

interface Props {
  driver: FaceDriver;
  param: Param;
  busy: boolean;
  onApply: (values: Record<string, number>) => void;
  onClose: () => void;
}

// Moves the picked face by an offset; the parameter changes by offset / rate.
export function FaceEdit({ driver, param, busy, onApply, onClose }: Props) {
  const [offset, setOffset] = useState("");
  const t = useT();
  const submit = (e: FormEvent) => {
    e.preventDefault();
    onApply({ [param.name]: +(param.value + Number(offset) / driver.rate).toFixed(6) });
  };
  return (
    <form className="ws-face" aria-label={t.face.form} onSubmit={submit}>
      <p className="ws-muted">
        {t.face.drives(driver.part, param.label, `${param.value} ${param.unit}`)} ·{" "}
        <span className="mono">{t.face.rate(driver.rate.toFixed(2))}</span>
      </p>
      <div className="ws-face-row">
        <label htmlFor="face-offset">{t.face.offset}</label>
        <input
          id="face-offset"
          className="mono"
          type="number"
          step="any"
          value={offset}
          onChange={(e) => setOffset(e.target.value)}
          required
        />
        <Button type="submit" variant="primary" disabled={busy || offset === ""}>
          {t.apply}
        </Button>
        <Button variant="ghost" onClick={onClose}>
          {t.close}
        </Button>
      </div>
    </form>
  );
}
