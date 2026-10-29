import { useEffect, useRef, useState } from "react";
import { useT } from "../i18n";
import { Icon } from "../ui/icons";

export interface DeliverProps {
  heading: string;
  links: [label: string, href: string][];
  fcstd?: { available: boolean; download: () => void } | undefined;
  publish?: (() => Promise<unknown>) | undefined;
  checkPrint?: (() => void) | undefined;
}

// One menu for everything that leaves the workspace: files, FreeCAD, Explore, the slicer check.
export function DeliverMenu({ heading, links, fcstd, publish, checkPrint }: DeliverProps) {
  const t = useT();
  const d = t.deliver;
  const menu = useRef<HTMLDetailsElement>(null);
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState<{ ok: boolean; text: string }>();
  useEffect(() => {
    if (!open) return;
    const outside = (e: PointerEvent) => {
      if (menu.current && !menu.current.contains(e.target as Node)) menu.current.open = false;
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);
  const close = () => {
    if (menu.current) menu.current.open = false;
  };
  return (
    <details
      ref={menu}
      className="menu ws-deliver"
      onToggle={(e) => setOpen(e.currentTarget.open)}
      onKeyDown={(e) => {
        if (e.key !== "Escape" || !open) return;
        close();
        menu.current?.querySelector("summary")?.focus();
      }}
    >
      <summary className="ui-button" data-variant="primary">
        <Icon name="deliver" />
        <span className="ws-wide">{d.deliver}</span>
      </summary>
      <div className="ws-menu">
        <h3 className="eyebrow">{heading}</h3>
        <ul>
          {links.map(([label, href]) => (
            <li key={label}>
              <a href={href} download onClick={close}>
                <Icon name="document" size={14} />
                {label}
              </a>
            </li>
          ))}
          {fcstd && (
            <li>
              <button
                type="button"
                disabled={!fcstd.available}
                aria-describedby={fcstd.available ? undefined : "ws-no-freecad"}
                onClick={() => {
                  close();
                  fcstd.download();
                }}
              >
                <Icon name="part" size={14} />
                {d.freecad}
              </button>
              {!fcstd.available && (
                <span id="ws-no-freecad" className="ws-menu-note">
                  {d.noFreecad}
                </span>
              )}
            </li>
          )}
        </ul>
        {(publish || checkPrint) && <hr />}
        <ul>
          {publish && (
            <li>
              <button
                type="button"
                onClick={() =>
                  publish().then(
                    () => setNote({ ok: true, text: d.published }),
                    (e: Error) => setNote({ ok: false, text: e.message }),
                  )
                }
              >
                <Icon name="globe" size={14} />
                {d.publish}
              </button>
            </li>
          )}
          {checkPrint && (
            <li>
              <button
                type="button"
                onClick={() => {
                  close();
                  checkPrint();
                }}
              >
                <Icon name="process" size={14} />
                {t.printability.check}
              </button>
            </li>
          )}
        </ul>
        {note && (
          <p role={note.ok ? "status" : "alert"} className={note.ok ? "ws-menu-note" : "ws-error"}>
            {note.text}
          </p>
        )}
      </div>
    </details>
  );
}
