// src/components/AuthLayout.jsx
// No CSS import needed — uses .auth-shell and .auth-main from Layout.css

export default function AuthLayout({ children }) {
  return (
    <div className="auth-shell">
      <main className="auth-main">
        {children}
      </main>
    </div>
  );
}
