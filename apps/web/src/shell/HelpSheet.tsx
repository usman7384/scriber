import { useT, type Messages } from "../i18n";
import { Button } from "../ui/Button";
import { Kbd } from "../ui/Kbd";
import { Sheet } from "../ui/Sheet";
import { useActions } from "./actions";
import { BUG_ACTION } from "./bug";
import { isMac, keyCaps, PALETTE_KEY } from "./keys";
import { useCloseSheet } from "./sheets";

// docs/design/UI_DIRECTION.md §5; the workspace and command bar register most of these.
const shortcuts: [string[], keyof Messages["help"]["keys"]][] = [
  [[PALETTE_KEY], "palette"],
  [["/"], "command"],
  [["1", "2", "3", "0"], "views"],
  [["e", "m", "p"], "overlays"],
  [["[", "]"], "versions"],
  [["escape"], "close"],
  [["enter"], "apply"],
  [["?"], "help"],
];

export function HelpSheet() {
  const t = useT();
  const close = useCloseSheet();
  const bug = useActions().find((a) => a.id === BUG_ACTION);
  const mac = isMac();
  const howTos: [string, string][] = [
    [t.help.make, t.help.makeText],
    [t.help.change, t.help.changeText],
    [t.help.context, t.help.contextText],
    [t.help.files, t.help.filesText],
  ];
  return (
    <Sheet
      open
      onClose={close}
      title={t.help.title}
      footer={
        <>
          {!bug && <p className="shell-note">{t.help.bugNeedsPart}</p>}
          <Button icon="warn" disabled={!bug} onClick={() => bug?.run("")}>
            {t.bug.open}
          </Button>
        </>
      }
    >
      <div className="shell-help">
        <table className="shell-keys">
          <caption>{t.help.shortcuts}</caption>
          <thead>
            <tr>
              <th scope="col">{t.help.key}</th>
              <th scope="col">{t.help.action}</th>
            </tr>
          </thead>
          <tbody>
            {shortcuts.map(([keys, what]) => (
              <tr key={what}>
                <td>
                  {keys.map((k) => (
                    <Kbd key={k} keys={keyCaps(k, mac, t.agent.command.ctrl)} />
                  ))}
                </td>
                <td>{t.help.keys[what]}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <h3>{t.help.howTo}</h3>
        {howTos.map(([title, text]) => (
          <section key={title} className="shell-howto">
            <h4>{title}</h4>
            <p>{text}</p>
          </section>
        ))}
      </div>
    </Sheet>
  );
}
