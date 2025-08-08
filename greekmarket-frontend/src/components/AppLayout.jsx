// src/components/AppLayout.jsx
import { Outlet, useLocation } from "react-router-dom";
import BottomNav from "./BottomNav";
import "../styles/Layout.css";

export default function AppLayout() {
  const location = useLocation();
  const isAuthPage = ["/login", "/signup"].includes(location.pathname);

  return (
    <div className={`app-shell ${isAuthPage ? "auth" : ""}`}>
      {!isAuthPage && <aside className="app-rail app-rail-left" aria-hidden />}
      <main className="app-main">
        <Outlet />
      </main>
      {!isAuthPage && <aside className="app-rail app-rail-right" aria-hidden />}
      {!isAuthPage && <BottomNav />}
    </div>
  );
}
