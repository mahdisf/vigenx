import { Braces, Eye, GitCompareArrows, ShieldCheck } from "lucide-react";

const principles = [
  {
    icon: Eye,
    title: "Inspectable by default",
    description: "See the nodes, edges, and parameters the planner selected before execution.",
  },
  {
    icon: GitCompareArrows,
    title: "Editable, not disposable",
    description: "Change the generated graph instead of restarting from another prompt.",
  },
  {
    icon: Braces,
    title: "Reproducible workflows",
    description: "Serialize the graph to JSON so the same decisions can be reviewed and rerun.",
  },
  {
    icon: ShieldCheck,
    title: "Human approval",
    description: "Treat the agent as a planner. You decide whether the workflow should execute.",
  },
];

export function PrinciplesSection() {
  return (
    <section className="section principles-section" id="principles" aria-labelledby="principles-title">
      <div className="shell principles-layout">
        <div className="section-heading principles-heading">
          <p className="section-label">Control is a feature</p>
          <h2 id="principles-title">Agentic does not mean opaque.</h2>
          <p>
            ViGenX separates planning from execution. That boundary makes automated editing easier to audit,
            modify, and repeat.
          </p>
        </div>

        <div className="principle-list">
          {principles.map((principle, index) => (
            <article className="principle" key={principle.title}>
              <span className="principle-number">0{index + 1}</span>
              <principle.icon aria-hidden="true" />
              <div>
                <h3>{principle.title}</h3>
                <p>{principle.description}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
