// src/App.jsx
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import AuthLayout from "./components/AuthLayout";

// Pages
import LoginPage from "./pages/LoginPage";
import SignUpPage from "./pages/SignUpPage";
import BrowsePage from "./pages/BrowsePage";
import DashboardPage from "./pages/DashboardPage";
import CreatePostPage from "./pages/CreatePostPage";
import PurchasesPage from "./pages/PurchasesPage";
import SearchPage from "./pages/SearchPage";

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Auth routes: force the hard-centering layout */}
        <Route
          path="/login"
          element={
            <AuthLayout>
              <LoginPage />
            </AuthLayout>
          }
        />
        <Route
          path="/signup"
          element={
            <AuthLayout>
              <SignUpPage />
            </AuthLayout>
          }
        />

        {/* Main app uses the standard layout with rails + bottom nav */}
        <Route element={<AppLayout />}>
          <Route path="/browse" element={<BrowsePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/create" element={<CreatePostPage />} />
          <Route path="/purchases" element={<PurchasesPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="*" element={<Navigate to="/browse" replace />} />
        </Route>
      </Routes>
    </Router>
  );
}
