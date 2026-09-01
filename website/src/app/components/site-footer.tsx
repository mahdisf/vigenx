import { Github } from "lucide-react";

const REPOSITORY_URL = "https://github.com/mahdisf/vigenx";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="shell footer-inner">
        <div>
          <a className="wordmark" href="#top" aria-label="ViGenX home">ViGenX<span aria-hidden="true">.</span></a>
          <p>Agentic video workflows you can inspect, edit, and approve.</p>
        </div>
        <nav aria-label="Project links">
          <a href={REPOSITORY_URL} target="_blank" rel="noreferrer"><Github aria-hidden="true" /> GitHub</a>
          <a href={`${REPOSITORY_URL}#readme`} target="_blank" rel="noreferrer">Docs</a>
          <a href={`${REPOSITORY_URL}/issues`} target="_blank" rel="noreferrer">Issues</a>
          <a href={`${REPOSITORY_URL}/discussions`} target="_blank" rel="noreferrer">Discussions</a>
        </nav>
      </div>
    </footer>
  );
}
