import { useEffect, useEffectEvent, useId, useState, type KeyboardEvent } from "react";
import { api, type Process } from "../api";
import { useT } from "../i18n";
import { Button } from "../ui/Button";
import { IconButton } from "../ui/IconButton";
import { Kbd } from "../ui/Kbd";
import { AttachButton, AttachmentTray } from "./AttachmentTray";
import { ProcessChip, QuantityField, SourceChips, TargetChip, type Target } from "./BarParts";
import { StarterCards } from "./StarterCards";
import { useAttachments } from "./useAttachments";
import { useSubmit, type OnJob } from "./useSubmit";
import "./agent.css";

interface Shared {
  onJob: OnJob;
  // Text after a leading "/" goes to the command palette; without this the bar only says so.
  onCommand?: (query: string) => void;
}

interface GenerateProps extends Shared {
  mode: "generate";
  projectId: string;
  contextIds: string[];
  starters?: boolean;
}

interface RefineProps extends Shared {
  mode: "refine";
  modelId: string;
  target?: Target | undefined;
  onClearTarget: () => void;
  busy?: boolean;
}

export type CommandBarProps = GenerateProps | RefineProps;

export function CommandBar(props: CommandBarProps) {
  return props.mode === "generate" ? <GenerateBar {...props} /> : <RefineBar {...props} />;
}

function GenerateBar({ projectId, contextIds, starters = true, onJob, onCommand }: GenerateProps) {
  const t = useT();
  const id = useId();
  const [text, setText] = useState("");
  const [process, setProcess] = useState<Process>("any");
  const tray = useAttachments(projectId);
  const { sending, error, submit } = useSubmit(onJob);
  const command = text.startsWith("/");

  const dropped = useEffectEvent((e: DragEvent) => {
    const files = [...(e.dataTransfer?.files ?? [])];
    if (e.defaultPrevented || files.length === 0) return;
    e.preventDefault();
    tray.add(files);
  });
  useEffect(() => {
    const over = (e: DragEvent) => e.dataTransfer?.types.includes("Files") && e.preventDefault();
    const drop = (e: DragEvent) => dropped(e);
    window.addEventListener("dragover", over);
    window.addEventListener("drop", drop);
    return () => {
      window.removeEventListener("dragover", over);
      window.removeEventListener("drop", drop);
    };
  }, []);

  const send = (e?: { preventDefault: () => void }) => {
    e?.preventDefault();
    if (command) {
      onCommand?.(text.slice(1).trim());
      return setText("");
    }
    if (sending || !text.trim()) return;
    const build = async () => {
      const attachments = await tray.settled();
      const context = contextIds.length > 0 && { context_ids: contextIds };
      const body = { prompt: text.trim(), process, attachments, ...context };
      return () => api.generate(projectId, body);
    };
    void submit(build, () => {
      setText("");
      tray.clear();
    });
  };
  const keys = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey || command)) send(e);
  };

  return (
    <div className="agent-composer">
      <form className="agent-bar" data-mode="generate" aria-label={t.prompt.form} onSubmit={send}>
        <QuantityField
          id={id}
          label={t.prompt.label}
          value={text}
          rows={3}
          placeholder={t.prompt.placeholder}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={keys}
          onPaste={(e) => {
            const files = [...e.clipboardData.files];
            if (files.length === 0) return;
            e.preventDefault();
            tray.add(files);
          }}
        />
        {command && <p className="agent-hint">{t.agent.command.command}</p>}
        <AttachmentTray items={tray.items} onRetry={tray.retry} onRemove={tray.remove} />
        <div className="agent-bar-row">
          <AttachButton onFiles={tray.add} />
          <ProcessChip value={process} onChange={setProcess} />
          <SourceChips projectId={projectId} ids={contextIds} />
          <span className="agent-spacer" />
          <Kbd keys={[t.agent.command.ctrl, t.agent.command.enter]} />
          <Button
            type="submit"
            variant="primary"
            icon="send"
            disabled={sending || !text.trim() || (command && !onCommand)}
          >
            {sending ? (tray.busy ? t.agent.command.waiting : t.prompt.starting) : t.prompt.generate}
          </Button>
        </div>
        {error && (
          <p role="alert" className="agent-error">
            {error}
          </p>
        )}
      </form>
      {starters && <StarterCards onPick={setText} />}
    </div>
  );
}

function RefineBar({ modelId, target, onClearTarget, busy = false, onJob, onCommand }: RefineProps) {
  const t = useT();
  const id = useId();
  const [text, setText] = useState("");
  const [process, setProcess] = useState<Process>("any");
  const { sending, error, submit } = useSubmit(onJob);
  const command = text.startsWith("/");

  const send = (e?: { preventDefault: () => void }) => {
    e?.preventDefault();
    if (command) {
      onCommand?.(text.slice(1).trim());
      return setText("");
    }
    if (busy || sending || !text.trim()) return;
    const body = {
      instruction: text.trim(),
      ...(target && { target: target.id }),
      ...(process !== "any" && { process }),
    };
    void submit(
      async () => () => api.refine(modelId, body),
      () => setText(""),
    );
  };
  const keys = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) send(e);
    if (e.key === "Backspace" && text === "" && target) onClearTarget();
  };
  const placeholder = busy
    ? t.agent.command.blocked
    : target
      ? t.agent.command.targetPlaceholder(target.label)
      : t.refine.placeholder;

  return (
    <form className="agent-bar" data-mode="refine" aria-label={t.refine.form} onSubmit={send}>
      <div className="agent-bar-row agent-bar-top">
        <TargetChip target={target} onClear={onClearTarget} />
        <QuantityField
          id={id}
          label={t.refine.label}
          value={text}
          rows={1}
          placeholder={placeholder}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={keys}
        />
      </div>
      {command && <p className="agent-hint">{t.agent.command.command}</p>}
      <div className="agent-bar-row">
        <ProcessChip value={process} onChange={setProcess} />
        <span className="agent-spacer" />
        <IconButton
          type="submit"
          variant="default"
          icon="send"
          label={t.refine.submit}
          disabled={busy || sending || !text.trim() || (command && !onCommand)}
        />
      </div>
      {error && (
        <p role="alert" className="agent-error">
          {error}
        </p>
      )}
    </form>
  );
}
