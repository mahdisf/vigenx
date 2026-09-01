import { useEffect, useState } from "react";
import { Github, Menu, X } from "lucide-react";

const REPOSITORY_URL = "https://github.com/mahdisf/vigenx";

const navigation = [
  { label: "Workflow", href: "#workflow" },
  { label: "Blocks", href: "#blocks" },
  { label: "Principles", href: "#principles" },
  { label: "Contribute", href: "#open-source" },
];

export function NavigationHeader() {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  return (
    <header className="site-header">
      <div className="shell header-inner">
        <a className="wordmark" href="#top" aria-label="ViGenX home">
          ViGenX<span aria-hidden="true">.</span>
        </a>

        <nav className="desktop-nav" aria-label="Primary navigation">
          {navigation.map((item) => (
            <a key={item.href} href={item.href}>
              {item.label}
            </a>
          ))}
        </nav>

        <a className="header-repo" href={REPOSITORY_URL} target="_blank" rel="noreferrer">
          <Github aria-hidden="true" />
          <span>GitHub</span>
        </a>

        <button
          className="menu-toggle"
          type="button"
          aria-expanded={isOpen}
          aria-controls="mobile-navigation"
          aria-label={isOpen ? "Close navigation" : "Open navigation"}
          onClick={() => setIsOpen((open) => !open)}
        >
          {isOpen ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
        </button>
      </div>

      <nav
        id="mobile-navigation"
        className="mobile-nav"
        aria-label="Mobile navigation"
        hidden={!isOpen}
      >
        {navigation.map((item) => (
          <a key={item.href} href={item.href} onClick={() => setIsOpen(false)}>
            {item.label}
          </a>
        ))}
        <a href={REPOSITORY_URL} target="_blank" rel="noreferrer" onClick={() => setIsOpen(false)}>
          GitHub repository
        </a>
      </nav>
    </header>
  );
}
