import { useT } from "../i18n";
import { useBugAction } from "../shell/bug";
import type { BugTarget } from "../shell/context";
import { Button } from "../ui/Button";

// Until the workspace (package B) calls useBugAction itself; the sheet lives in the shell.
export function BugDialog(target: BugTarget) {
  const open = useBugAction(target);
  const t = useT();
  return (
    <Button variant="ghost" onClick={open}>
      {t.bug.open}
    </Button>
  );
}
