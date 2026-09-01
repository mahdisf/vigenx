import { ArrowDown, ArrowUpRight, Github } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";

const REPOSITORY_URL = "https://github.com/mahdisf/vigenx";

export function HeroSection() {
  const reduceMotion = useReducedMotion();
  const productMedia =
    import.meta.env.BASE_URL === "/"
      ? "/product-workflow.png"
      : `${import.meta.env.BASE_URL}product-workflow.png`;

  const enter = (delay: number) => ({
    initial: reduceMotion ? false : { opacity: 0, y: 16 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: reduceMotion ? 0 : 0.5, delay: reduceMotion ? 0 : delay },
  });

  return (
    <section className="hero" id="top" aria-labelledby="hero-title">
      <div className="hero-grid" aria-hidden="true" />
      <div className="shell hero-inner">
        <motion.div className="hero-copy" {...enter(0)}>
          <p className="eyebrow">
            <span aria-hidden="true" /> Open-source agentic video editor
          </p>
          <h1 id="hero-title">ViGenX</h1>
          <p className="hero-statement">
            Describe an edit; get an inspectable, editable, reproducible workflow with human approval.
          </p>
          <p className="hero-detail">
            ViGenX turns plain-language intent into a validated graph of video operations. Review the plan,
            adjust any block, then choose when it runs.
          </p>

          <div className="hero-actions" aria-label="Project links">
            <a className="button button-primary" href={REPOSITORY_URL} target="_blank" rel="noreferrer">
              <Github aria-hidden="true" />
              View source
              <ArrowUpRight aria-hidden="true" />
            </a>
            <a
              className="button button-secondary"
              href={`${REPOSITORY_URL}#readme`}
              target="_blank"
              rel="noreferrer"
            >
              Read the docs
            </a>
          </div>
        </motion.div>

        <motion.figure className="product-figure" {...enter(0.14)}>
          <div className="product-rail" aria-hidden="true">
            <span>ViGenX / Editor</span>
            <span className="rail-state"><i /> Workflow ready for review</span>
          </div>
          <div className="product-media">
            <img
              src={productMedia}
              alt="ViGenX workflow editor with a plain-language brief and an editable node graph"
              width="1600"
              height="980"
              fetchPriority="high"
            />
          </div>
          <figcaption>
            The workflow is the product: visible before execution, editable before approval, reusable after export.
          </figcaption>
        </motion.figure>
      </div>

      <a className="section-cue" href="#workflow">
        Follow the workflow <ArrowDown aria-hidden="true" />
      </a>
    </section>
  );
}
