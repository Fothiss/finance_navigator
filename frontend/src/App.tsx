import { NavLink, Route, Routes } from "react-router-dom";
import History from "./pages/History";
import Money from "./pages/Money";
import Profile from "./pages/Profile";
import Risk from "./pages/Risk";
import Tax from "./pages/Tax";

const links = [
  { to: "/money", label: "Стоимость денег" },
  { to: "/risk", label: "Валютный риск" },
  { to: "/tax", label: "Налоговый прогноз" },
  { to: "/profile", label: "Профиль" },
  { to: "/history", label: "История" },
];

export default function App() {
  return (
    <div className="min-h-screen bg-white text-ink">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-6 py-4">
          <span className="text-lg font-semibold">Финансовый навигатор</span>
          <nav className="flex flex-wrap gap-3 text-sm">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  isActive ? "rounded bg-accent px-3 py-1 text-white" : "rounded px-3 py-1 text-muted hover:text-ink"
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-6">
        <Routes>
          <Route path="/" element={<Money />} />
          <Route path="/money" element={<Money />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/tax" element={<Tax />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </main>
    </div>
  );
}
