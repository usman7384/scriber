import { lazy, Suspense } from "react";
import { Route, Routes, useLocation } from "react-router";
import { Pending } from "./components/Pending";
import { Shell } from "./components/Shell";
import { useT } from "./i18n";
import { CommunityPage } from "./pages/CommunityPage";
import { ContextPage } from "./pages/ContextPage";
import { LibraryPage } from "./pages/LibraryPage";
import { ProjectPage } from "./pages/ProjectPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { HelpSheet } from "./shell/HelpSheet";
import { SettingsSheet } from "./shell/SettingsSheet";
import { ShellProvider } from "./shell/ShellProvider";
import { backdropOf, sheetOf } from "./shell/sheets";

const EditorPage = lazy(() => import("./pages/EditorPage").then((m) => ({ default: m.EditorPage })));
const SharedPage = lazy(() => import("./pages/SharedPage").then((m) => ({ default: m.SharedPage })));

export function App() {
  const location = useLocation();
  const sheet = sheetOf(location.pathname);
  return (
    <ShellProvider>
      {/* /settings and /help are sheets over the page they were opened from (Home for a deep link). */}
      <Routes location={backdropOf(location)}>
        <Route element={<Shell />}>
          <Route index element={<ProjectsPage />} />
          <Route path="library" element={<LibraryPage />} />
          <Route path="explore" element={<CommunityPage />} />
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
      {sheet === "settings" && <SettingsSheet />}
      {sheet === "help" && <HelpSheet />}
    </ShellProvider>
  );
}

function NotFound() {
  return <p className="empty">{useT().notFound}</p>;
}
