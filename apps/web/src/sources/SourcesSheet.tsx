import { useState } from "react";
import { api } from "../api";
import { Pending } from "../components/Pending";
import { useResource } from "../hooks";
import { useT } from "../i18n";
import { Button } from "../ui/Button";
import { Sheet } from "../ui/Sheet";
import { FactList } from "./FactList";
import { FileList } from "./FileList";
import { GraphView } from "./GraphView";
import { KnowledgeMeter } from "./KnowledgeMeter";
import { RulesList } from "./RulesList";
import { UploadZone } from "./UploadZone";
import "./sources.css";

interface Props {
  projectId: string;
  onClose: () => void;
  onUse: (fileIds: string[]) => void;
}

export function SourcesSheet({ projectId, onClose, onUse }: Props) {
  const context = useResource(`context:${projectId}`, () => api.context(projectId));
  const rules = useResource(`rules:${projectId}`, () => api.rules(projectId));
  const graph = useResource(`graph:${projectId}`, () => api.graph(projectId));
  const models = useResource(`models:${projectId}`, () => api.models(projectId));
  const [open, setOpen] = useState<string>();
  const [chosen, setChosen] = useState<string[]>([]);
  const [error, setError] = useState<string>();
  const t = useT();

  const refresh = () => {
    context.reload();
    rules.reload();
    graph.reload();
  };
  const remove = (fileId: string) =>
    api.deleteFile(projectId, fileId).then(refresh, (e: Error) => setError(e.message));
  const openFile = context.data?.files.find((f) => f.id === open);
  const footer = chosen.length > 0 && (
    <>
      <Button variant="ghost" onClick={() => setChosen([])}>
        {t.clear}
      </Button>
      <Button variant="primary" onClick={() => onUse(chosen)}>
        {t.context.useSelected(chosen.length)}
      </Button>
    </>
  );

  return (
    <Sheet open onClose={onClose} title={t.context.title} footer={footer}>
      <div className="sources-sheet">
        {context.data && <KnowledgeMeter stats={context.data.stats} />}
        <UploadZone projectId={projectId} onChange={refresh} />
        {error && (
          <p role="alert" className="src-error">
            {error}
          </p>
        )}
        {context.data ? (
          <FileList
            files={context.data.files}
            open={open}
            chosen={chosen}
            titles={Object.fromEntries((models.data ?? []).map((m) => [m.id, m.title]))}
            onOpen={setOpen}
            onChoose={setChosen}
            onDelete={remove}
          />
        ) : (
          <Pending error={context.error} />
        )}
        {openFile && (
          <section aria-label={t.context.factsFrom(openFile.name)}>
            <h3 className="eyebrow src-section-head">{openFile.name}</h3>
            <FactList projectId={projectId} fileId={openFile.id} />
          </section>
        )}
        <section>
          <h3 className="eyebrow src-section-head">{t.context.rules}</h3>
          {rules.data ? <RulesList rules={rules.data} /> : <Pending error={rules.error} />}
        </section>
        {graph.data ? <GraphView graph={graph.data} /> : <Pending error={graph.error} />}
      </div>
    </Sheet>
  );
}
