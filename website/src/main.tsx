import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./app/App";
import "./styles/index.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("ViGenX could not find the application root.");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
