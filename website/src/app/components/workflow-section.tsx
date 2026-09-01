import { ArrowRight, Check, FileJson2, MessageSquareText, SlidersHorizontal } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";

const steps = [
  {
    number: "01",
    icon: MessageSquareText,
    title: "Describe the edit",
    description: "Give ViGenX a source and a plain-language brief. Intent stays attached to the generated plan.",
  },
  {
    number: "02",
    icon: FileJson2,
    title: "Inspect the graph",
    description: "The planner selects registered blocks, validates their connections, and returns serializable JSON.",
  },
  {
    number: "03",
    icon: SlidersHorizontal,
    title: "Edit and approve",
    description: "Change parameters or connections in the visual editor. Execution remains behind a human decision.",
  },
];

const graphNodes = ["Source", "Transcribe", "Find moments", "Reframe", "Captions", "Export"];

export function WorkflowSection() {
  const reduceMotion = useReducedMotion();

  return (
    <section className="section workflow-section" id="workflow" aria-labelledby="workflow-title">
      <div className="shell">
        <motion.div
          className="section-heading section-heading-wide"
          initial={reduceMotion ? false : { opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: reduceMotion ? 0 : 0.45 }}
        >
          <p className="section-label">Intent becomes structure</p>
          <h2 id="workflow-title">A plan you can read before it touches the timeline.</h2>
          <p>
            The agent does not return a mystery render. It compiles your request into a typed workflow made from
            known operations, then exposes that workflow for review.
          </p>
        </motion.div>

        <div className="brief-to-graph">
          <div className="brief-panel">
            <div className="panel-label">Example brief</div>
            <blockquote>
              &ldquo;Turn this interview into vertical clips. Keep the speaker centered, add readable captions, and
              prepare a high-quality export.&rdquo;
            </blockquote>
            <div className="brief-status"><Check aria-hidden="true" /> Ready to plan</div>
          </div>

          <div className="graph-panel" aria-label="Example generated workflow">
            <div className="panel-label">Validated workflow</div>
            <div className="graph-track">
              {graphNodes.map((node, index) => (
                <div className="graph-item" key={node}>
                  <div className="graph-node">
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    {node}
                  </div>
                  {index < graphNodes.length - 1 ? <ArrowRight aria-hidden="true" /> : null}
                </div>
              ))}
            </div>
            <div className="graph-meta">
              <span>Editable parameters</span>
              <span>Serializable graph</span>
              <span>Approval required</span>
            </div>
          </div>
        </div>

        <div className="step-list">
          {steps.map((step) => (
            <article className="step" key={step.number}>
              <div className="step-topline">
                <span>{step.number}</span>
                <step.icon aria-hidden="true" />
              </div>
              <h3>{step.title}</h3>
              <p>{step.description}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
