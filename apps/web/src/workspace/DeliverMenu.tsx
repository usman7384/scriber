import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useT } from "../i18n";
import { useRegisterActions, type Action } from "../shell/actions";
import { Button } from "../ui/Button";
import { Icon } from "../ui/icons";

export interface DeliverProps {
  heading: string;
  links: [label: string, href: string][];
  fcstd?: { available: boolean; download: () => void } | undefined;
  share?: { create: () => Promise<{ id: string }>; revoke: (id: string) => Promise<unknown> } | undefined;
  publish?: (() => Promise<unknown>) | undefined;
  checkPrint?: (() => void) | undefined;
}

const download = (href: string) => {
  const link = document.createElement("a");
  link.href = href;
  link.download = "";
  link.click();
};

// One menu for everything that leaves the workspace: files, FreeCAD, a share link, Explore, the slicer check.
// Each item is also a palette action doing the same, with the menu opened to show its result.
export function DeliverMenu({ heading, links, fcstd, share, publish, checkPrint }: DeliverProps) {
  const t = useT();
  const d = t.deliver;
  const menu = useRef<HTMLDetailsElement>(null);
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState<{ ok: boolean; text: string }>();
  const [shared, setShared] = useState<{ id: string; url: string }>();
  useEffect(() => {
    if (!open) return;
    const outside = (e: PointerEvent) => {
      if (menu.current && !menu.current.contains(e.target as Node)) menu.current.open = false;
    };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);
  const setMenu = (on: boolean) => {
    if (menu.current) menu.current.open = on;
  };
  const fail = (e: Error) => setNote({ ok: false, text: e.message });

  const run = {
    fcstd: () => {
      setMenu(false);
      fcstd?.download();
    },
    share: () => {
      setMenu(true);
      setNote(undefined);
      share
        ?.create()
        .then((s) => setShared({ id: s.id, url: new URL(`/shared/${s.id}`, location.href).href }), fail);
    },
    publish: () => {
      setMenu(true);
      publish?.().then(() => setNote({ ok: true, text: d.published }), fail);
    },
    print: () => {
      setMenu(false);
      checkPrint?.();
    },
  };
  const latest = useRef(run);
  useEffect(() => {
    latest.current = run;
  });
  const call = useCallback((id: keyof typeof run) => latest.current[id](), []);
  const revoke = (id: string) =>
    share?.revoke(id).then(() => {
      setShared(undefined);
      setNote({ ok: true, text: t.share.revoked });
    }, fail);

  const offered = (["fcstd", "share", "publish", "print"] as const)
    .filter((id) => ({ fcstd: fcstd?.available, share, publish, print: checkPrint })[id])
    .join(" ");
  const exports = JSON.stringify(links);
  const actions = useMemo<Action[]>(() => {
    const labels = {
      fcstd: t.editor.exportAs(t.deliver.freecad),
      share: t.share.share,
      publish: t.deliver.publish,
      print: t.printability.check,
    };
    const icons = { fcstd: "part", share: "globe", publish: "globe", print: "process" } as const;
    const files = JSON.parse(exports) as [string, string][];
    return [
      ...files.map(([label, href]): Action => ({
        id: `deliver.${label}`,
        group: "deliver",
        icon: "document",
        label: (m) => m.editor.exportAs(label),
        run: () => download(href),
      })),
      ...offered
        .split(" ")
        .filter(Boolean)
        .map((id): Action => {
          const key = id as keyof typeof labels;
          return {
            id: `deliver.${key}`,
            group: "deliver",
            icon: icons[key],
            label: () => labels[key],
            run: () => call(key),
          };
        }),
    ];
  }, [call, t, exports, offered]);
  useRegisterActions(actions);

  return (
    <details
      ref={menu}
      className="menu ws-deliver"
      onToggle={(e) => setOpen(e.currentTarget.open)}
      onKeyDown={(e) => {
        if (e.key !== "Escape" || !open) return;
        setMenu(false);
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
              <a href={href} download onClick={() => setMenu(false)}>
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
                onClick={run.fcstd}
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
        {(share || publish || checkPrint) && <hr />}
        <ul>
          {share && (
            <li>
              <button type="button" onClick={run.share}>
                <Icon name="globe" size={14} />
                {t.share.share}
              </button>
              {shared && (
                <div className="ws-share-row">
                  <input
                    readOnly
                    className="mono"
                    value={shared.url}
                    aria-label={t.share.link}
                    onFocus={(e) => e.target.select()}
                  />
                  <Button onClick={() => void navigator.clipboard.writeText(shared.url)}>
                    {t.share.copy}
                  </Button>
                  <Button variant="ghost" onClick={() => void revoke(shared.id)}>
                    {t.share.revoke}
                  </Button>
                </div>
              )}
            </li>
          )}
          {publish && (
            <li>
              <button type="button" onClick={run.publish}>
                <Icon name="globe" size={14} />
                {d.publish}
              </button>
            </li>
          )}
          {checkPrint && (
            <li>
              <button type="button" onClick={run.print}>
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
