import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router";
import { Pending } from "./components/Pending";
import { Shell } from "./components/Shell";
import { ContextPage } from "./pages/ContextPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ProjectsPage } from "./pages/ProjectsPage";

const EditorPage = lazy(() => import("./pages/EditorPage").then((m) => ({ default: m.EditorPage })));

export function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<ProjectsPage />} />
        <Route path="p/:projectId" element={<ProjectPage />} />
        <Route path="p/:projectId/context" element={<ContextPage />} />
        <Route
          path="m/:modelId"
          element={
            <Suspense fallback={<Pending />}>
              <EditorPage />
            </Suspense>
          }
        />
        <Route path="*" element={<p className="empty">Page not found.</p>} />
      </Route>
    </Routes>
  );
}
