import { api } from "../api";
import { ModelGallery } from "../components/ModelGallery";
import { Pending } from "../components/Pending";
import { useResource } from "../hooks";
import { useT } from "../i18n";

const allModels = async () => (await Promise.all((await api.projects()).map((p) => api.models(p.id)))).flat();

export function LibraryPage() {
  const models = useResource("library", allModels);
  const t = useT();
  return (
    <section className="stack">
      <h1>{t.nav.library}</h1>
      {models.data ? <ModelGallery models={models.data} /> : <Pending error={models.error} />}
    </section>
  );
}
