import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import "highlight.js/styles/github-dark.css";

// Initialize theme from localStorage or system preference
(function initTheme() {
  try {
    const stored = localStorage.getItem("theme");
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const shouldDark = stored ? stored === "dark" : prefersDark;
    document.documentElement.classList.toggle("dark", shouldDark);
  } catch {}
})();

createRoot(document.getElementById("root")!).render(<App />);
