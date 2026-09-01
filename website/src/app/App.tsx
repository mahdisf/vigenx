import { BuildingBlocksSection } from "./components/building-blocks-section";
import { HeroSection } from "./components/hero-section";
import { NavigationHeader } from "./components/navigation-header";
import { OpenSourceSection } from "./components/open-source-section";
import { PrinciplesSection } from "./components/principles-section";
import { SiteFooter } from "./components/site-footer";
import { WorkflowSection } from "./components/workflow-section";

export default function App() {
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <NavigationHeader />
      <main id="main-content">
        <HeroSection />
        <WorkflowSection />
        <BuildingBlocksSection />
        <PrinciplesSection />
        <OpenSourceSection />
      </main>
      <SiteFooter />
    </>
  );
}
