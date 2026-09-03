import { SiteFooter } from "@/components/site-footer"
import { SiteHeader } from "@/components/site-header"
import { CtaBand } from "@/components/sections/cta-band"
import { Faq } from "@/components/sections/faq"
import { Features } from "@/components/sections/features"
import { Governance } from "@/components/sections/governance"
import { Hero } from "@/components/sections/hero"
import { HowItWorks } from "@/components/sections/how-it-works"
import { Impact } from "@/components/sections/impact"
import { Problem } from "@/components/sections/problem"
import { Rationale } from "@/components/sections/rationale"
import { Roadmap } from "@/components/sections/roadmap"

export default function App() {
  return (
    <div className="min-h-screen bg-background">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[60] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-base focus:font-semibold focus:text-primary-foreground"
      >
        Skip to main content
      </a>

      <SiteHeader />

      <main id="main">
        <Hero />
        <Problem />
        <Rationale />
        <HowItWorks />
        <Features />
        <Impact />
        <Roadmap />
        <Governance />
        <Faq />
        <CtaBand />
      </main>

      <SiteFooter />
    </div>
  )
}
