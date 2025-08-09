// src/App.jsx
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "./components/AppLayout";

// Pages
import LoginPage from "./pages/LoginPage";
import SignUpPage from "./pages/SignUpPage";
import BrowsePage from "./pages/BrowsePage";
import DashboardPage from "./pages/DashboardPage";
import CreatePostPage from "./pages/CreatePostPage";
import PurchasesPage from "./pages/PurchasesPage";
import SearchPage from "./pages/SearchPage";
import SchoolPage from "./pages/SchoolPage";
import ChapterPage from "./pages/ChapterPage";  // ⬅️ NEW

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Auth routes OUTSIDE the layout so they use the full viewport */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignUpPage />} />

        {/* Main app uses the layout */}
        <Route element={<AppLayout />}>
          <Route path="/browse" element={<BrowsePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/create" element={<CreatePostPage />} />
          <Route path="/purchases" element={<PurchasesPage />} />
          <Route path="/search" element={<SearchPage />} />

          {/* Details */}
          <Route path="/school/:id" element={<SchoolPage />} />
          <Route path="/chapter/:id" element={<ChapterPage />} /> {/* ⬅️ NEW */}

          {/* Default redirect */}
          <Route path="*" element={<Navigate to="/browse" replace />} />
        </Route>
      </Routes>
    </Router>
  );
}
