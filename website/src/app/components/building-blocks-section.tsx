import {
  Captions,
  FileInput,
  Focus,
  Scissors,
  Sparkles,
  Upload,
  Volume2,
} from "lucide-react";

const blocks = [
  {
    icon: FileInput,
    stage: "Input",
    title: "Bring in a source",
    description: "Start with a local video or a supported remote source, then carry its metadata through the graph.",
  },
  {
    icon: Captions,
    stage: "Understand",
    title: "Transcribe speech",
    description: "Generate timed transcript data that downstream blocks can use for selection and captions.",
  },
  {
    icon: Sparkles,
    stage: "Select",
    title: "Find key moments",
    description: "Use deterministic scoring or configured AI blocks to identify candidate segments.",
  },
  {
    icon: Scissors,
    stage: "Edit",
    title: "Cut and assemble",
    description: "Trim silence, cut moments, and compose clips through explicit graph operations.",
  },
  {
    icon: Focus,
    stage: "Frame",
    title: "Reframe the action",
    description: "Build vertical outputs with crop, fit, and background treatments where the workflow calls for them.",
  },
  {
    icon: Volume2,
    stage: "Finish",
    title: "Caption and mix",
    description: "Burn subtitles, add configured audio layers, and keep each finishing choice visible in the plan.",
  },
];

export function BuildingBlocksSection() {
  return (
    <section className="section blocks-section" id="blocks" aria-labelledby="blocks-title">
      <div className="shell">
        <div className="section-heading">
          <p className="section-label">Composable operations</p>
          <h2 id="blocks-title">Useful building blocks, assembled for the job.</h2>
          <p>
            ViGenX plans against a registered catalog. The graph can combine media analysis, editing, audio, and
            export operations without inventing unavailable tools.
          </p>
        </div>

        <div className="block-grid">
          {blocks.map((block) => (
            <article className="block-card" key={block.title}>
              <div className="block-icon"><block.icon aria-hidden="true" /></div>
              <p className="block-stage">{block.stage}</p>
              <h3>{block.title}</h3>
              <p>{block.description}</p>
            </article>
          ))}
        </div>

        <div className="export-line">
          <Upload aria-hidden="true" />
          <p><strong>Export is still a block.</strong> Output settings and metadata remain part of the workflow.</p>
        </div>
      </div>
    </section>
  );
}
