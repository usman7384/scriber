import { lazy, Suspense } from "react";
import { Outlet, Route, Routes, useLocation } from "react-router";
import { Pending } from "./components/Pending";
import { ExplorePage } from "./home/ExplorePage";
import { HomeLayout } from "./home/HomeLayout";
import { HomePage } from "./home/HomePage";
import { useT } from "./i18n";
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
        <Route index element={<HomePage />} />
        <Route path="library" element={<HomePage />} />
        <Route path="p/:projectId" element={<HomePage />} />
        <Route path="p/:projectId/context" element={<HomePage />} />
        <Route path="explore" element={<ExplorePage />} />
        <Route element={<Stage />}>
          <Route path="m/:modelId" element={<EditorPage />} />
          <Route path="shared/:shareId" element={<SharedPage />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
      {sheet === "settings" && <SettingsSheet />}
      {sheet === "help" && <HelpSheet />}
    </ShellProvider>
  );
}

// Model routes: the workspace covers the window and brings its own top bar.
function Stage() {
  return (
    <main>
      <Suspense fallback={<Pending />}>
        <Outlet />
      </Suspense>
    </main>
  );
}

function NotFound() {
  return (
    <HomeLayout>
      <p className="home-empty">{useT().notFound}</p>
    </HomeLayout>
  );
}
