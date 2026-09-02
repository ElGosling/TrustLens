import { ExternalLink, ScanEye } from "lucide-react"

import { TELEGRAM_BOT_HANDLE, TELEGRAM_BOT_URL } from "@/lib/utils"

const SECTION_LINKS = [
  { href: "#problem", label: "The problem" },
  { href: "#rationale", label: "Our rationale" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#features", label: "Features" },
  { href: "#impact", label: "Intended impact" },
  { href: "#roadmap", label: "Roadmap" },
  { href: "#trust", label: "Trust and data handling" },
  { href: "#faq", label: "Common questions" },
]

const REFERENCES = [
  {
    label: "IMDA, Digital Skills for Life Framework",
    href: "https://www.digitalforlife.gov.sg/about/news-releases/new-digital-skills-for-life-framework",
  },
  {
    label: "Ipsos (2025), The Susceptibility of Singaporeans Towards Fake News",
    href: "https://www.ipsos.com/en-sg/susceptibility-singaporeans-towards-fake-news",
  },
  {
    label: "IPS, Singaporeans' Susceptibility to False Information",
    href: "https://lkyspp.nus.edu.sg/docs/default-source/ips/ips-exchange-series-19.pdf",
  },
  {
    label: "SUTD, Local Perceptions and Practices of News Sharing and Fake News",
    href: "https://arxiv.org/html/2010.07607v2",
  },
  {
    label: "NTU (2025), More fake news online now, survey finds",
    href: "https://www.ntu.edu.sg/research/research-hub/more-fake-news-online-now-survey-finds",
  },
  {
    label: "IMDA, Digital Readiness",
    href: "https://www.imda.gov.sg/for-community/digital-readiness",
  },
]

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-background">
      <div className="container grid gap-12 py-14 lg:grid-cols-[1.2fr_1fr_1.4fr]">
        <div>
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-md bg-primary">
              <ScanEye aria-hidden="true" className="h-6 w-6 text-primary-foreground" />
            </span>
            <span className="text-xl font-bold tracking-tight text-foreground">
              TrustLens<span className="text-primary"> SG</span>
            </span>
          </div>
          <p className="mt-4 max-w-sm text-base leading-relaxed text-muted-foreground">
            A fact-checking and media-literacy companion that works inside the
            messaging apps Singaporeans already use.
          </p>
          <a
            href={TELEGRAM_BOT_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-5 inline-flex items-center gap-2 rounded-md text-base font-semibold text-primary underline-offset-4 hover:underline"
          >
            {TELEGRAM_BOT_HANDLE} on Telegram
            <ExternalLink aria-hidden="true" className="h-4 w-4" />
          </a>
        </div>

        <nav aria-label="Footer">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-foreground">
            On this page
          </h2>
          <ul className="mt-4 space-y-2.5">
            {SECTION_LINKS.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  className="rounded-md text-base text-muted-foreground underline-offset-4 hover:text-primary hover:underline"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div>
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-foreground">
            Research this project draws on
          </h2>
          <ul className="mt-4 space-y-2.5">
            {REFERENCES.map((reference) => (
              <li key={reference.href}>
                <a
                  href={reference.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-start gap-1.5 rounded-md text-base text-muted-foreground underline-offset-4 hover:text-primary hover:underline"
                >
                  <span>{reference.label}</span>
                  <ExternalLink
                    aria-hidden="true"
                    className="mt-1.5 h-3.5 w-3.5 shrink-0"
                  />
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="border-t border-border bg-muted">
        <div className="container flex flex-col gap-3 py-6 md:flex-row md:items-center md:justify-between">
          <p className="text-sm text-muted-foreground">
            TrustLens SG is an independent student-led project by Team terrafic,
            Singapore Management University. It is not a government agency and
            not an official government service.
          </p>
          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} Team terrafic
          </p>
        </div>
      </div>
    </footer>
  )
}
