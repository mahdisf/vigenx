import { ArrowUpRight, GitFork, Github, MessageCircle, SquareTerminal } from "lucide-react";

const REPOSITORY_URL = "https://github.com/mahdisf/vigenx";

const contributionLinks = [
  { label: "Browse the code", href: REPOSITORY_URL, icon: Github },
  { label: "Open an issue", href: `${REPOSITORY_URL}/issues`, icon: SquareTerminal },
  { label: "Start a discussion", href: `${REPOSITORY_URL}/discussions`, icon: MessageCircle },
];

export function OpenSourceSection() {
  return (
    <section className="section open-source-section" id="open-source" aria-labelledby="open-source-title">
      <div className="shell open-source-layout">
        <div>
          <p className="section-label">Built in public</p>
          <h2 id="open-source-title">Use it. Stress it. Help shape what comes next.</h2>
          <p className="open-source-copy">
            ViGenX is an early-stage open-source project. Try it on footage you are allowed to edit, report exact
            failures, and contribute blocks, planner improvements, evaluation cases, or documentation.
          </p>

          <div className="contribution-links">
            {contributionLinks.map((link) => (
              <a key={link.label} href={link.href} target="_blank" rel="noreferrer">
                <link.icon aria-hidden="true" />
                <span>{link.label}</span>
                <ArrowUpRight aria-hidden="true" />
              </a>
            ))}
          </div>
        </div>

        <aside className="clone-panel" aria-label="Clone ViGenX">
          <div className="clone-title"><GitFork aria-hidden="true" /> Start from the repository</div>
          <code>git clone https://github.com/mahdisf/vigenx.git</code>
          <div className="clone-links">
            <a href={`${REPOSITORY_URL}/blob/master/CONTRIBUTING.md`} target="_blank" rel="noreferrer">
              Contribution guide <ArrowUpRight aria-hidden="true" />
            </a>
            <a href={`${REPOSITORY_URL}/tree/master/docs`} target="_blank" rel="noreferrer">
              Project docs <ArrowUpRight aria-hidden="true" />
            </a>
          </div>
        </aside>
      </div>
    </section>
  );
}
