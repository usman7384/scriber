import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router";
import { Pending } from "./components/Pending";
import { Shell } from "./components/Shell";
import { useT } from "./i18n";
import { ContextPage } from "./pages/ContextPage";
import { HelpPage } from "./pages/HelpPage";
import { LibraryPage } from "./pages/LibraryPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SettingsPage } from "./pages/SettingsPage";

const EditorPage = lazy(() => import("./pages/EditorPage").then((m) => ({ default: m.EditorPage })));
const SharedPage = lazy(() => import("./pages/SharedPage").then((m) => ({ default: m.SharedPage })));

export function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<ProjectsPage />} />
        <Route path="library" element={<LibraryPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="help" element={<HelpPage />} />
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
        <Route
          path="shared/:shareId"
          element={
            <Suspense fallback={<Pending />}>
              <SharedPage />
            </Suspense>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

function NotFound() {
  return <p className="empty">{useT().notFound}</p>;
}
