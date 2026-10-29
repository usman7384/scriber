import { api } from "../api";
import { ModelGallery } from "../components/ModelGallery";
import { Pending } from "../components/Pending";
import { useResource } from "../hooks";

const allModels = async () => (await Promise.all((await api.projects()).map((p) => api.models(p.id)))).flat();

export function LibraryPage() {
  const models = useResource("library", allModels);
  return (
    <section className="stack">
      <h1>Library</h1>
      {models.data ? <ModelGallery models={models.data} /> : <Pending error={models.error} />}
    </section>
  );
}
