import { Link, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { DownloadsPage } from "@/pages/DownloadsPage";
import { HomePage } from "@/pages/HomePage";
import { SettingsPage } from "@/pages/SettingsPage";
import { RealtimeProvider } from "@/realtime/RealtimeProvider";

function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
      <p className="text-sm uppercase tracking-[0.3em] text-faint">404</p>
      <h1 className="text-2xl font-semibold text-ink">This page does not exist</h1>
      <Link to="/" className="text-sm text-accent hover:underline">
        Back to downloader
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <RealtimeProvider>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<HomePage />} />
          <Route path="downloads" element={<DownloadsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </RealtimeProvider>
  );
}
