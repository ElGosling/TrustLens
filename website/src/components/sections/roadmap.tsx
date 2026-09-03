import { Banknote, CircleDot, Globe2, Server } from "lucide-react"

import { SectionHeading } from "@/components/section-heading"
import { Badge } from "@/components/ui/badge"

type PhaseStatus = "Live today" | "In development" | "Next" | "Longer term"

const STATUS_VARIANT: Record<PhaseStatus, "success" | "warning" | "info" | "outline"> = {
  "Live today": "success",
  "In development": "warning",
  Next: "info",
  "Longer term": "outline",
}

interface Phase {
  phase: string
  status: PhaseStatus
  title: string
  summary: string
  items: string[]
}

const PHASES: Phase[] = [
  {
    phase: "Phase 1",
    status: "Live today",
    title: "The working Telegram bot",
    summary:
      "The core loop is running. Send a message or a forwarded link and get back a cited verdict, built on a reviewed registry of trusted sources rather than the model's memory.",
    items: [
      "Text claims and forwarded links checked end to end on Telegram",
      "Version-controlled registry of approved sources and domains",
      "Verdicts of True, False, Misleading, Satire or Unverified with confidence and citations",
      "A deliberate Unverified answer whenever no approved source covers the claim",
      "The /quiz recap, built from the claims each user checked, with accuracy and daily streaks",
    ],
  },
  {
    phase: "Phase 2",
    status: "In development",
    title: "Every format, every language",
    summary:
      "Extending the same checked pipeline beyond text, and making it usable by people who do not read English comfortably or do not like typing.",
    items: [
      "Photo, video and voice note checking, including deepfake and voice-clone detection",
      "All four official languages, with Singlish-aware reading of messages",
      "Voice-first mode for seniors, so a message can be checked by speaking",
      "The shareable verified card as an image, ready to forward back into a group",
      "Recap quizzes that also cover checked photos, voice notes and non-English messages",
    ],
  },
  {
    phase: "Phase 3",
    status: "Next",
    title: "Reach beyond one chat at a time",
    summary:
      "Moving from an individual tool to a community one, tested properly before it goes wide.",
    items: [
      "WhatsApp as a second channel, alongside Telegram",
      "Browser extension placing credibility badges on social feeds",
      "Community trust layer: user flags, votes on ambiguous cases and contributed corrections",
      "Educator and employer dashboard with privacy-preserving cohort analytics",
      "Automatic escalation of likely scams to the relevant national reporting channel",
      "Closed pilot with two to three community clubs and one school, then public beta",
    ],
  },
  {
    phase: "Phase 4",
    status: "Longer term",
    title: "From reacting to warning early",
    summary:
      "Catching a false claim while it is still small, and extending the protection past messaging apps entirely.",
    items: [
      "Opt-in monitoring of public broadcast channels and trending topics to flag viral claims before they peak",
      "Dedicated audio forensics for AI voice-cloning scams",
      "Adaptive literacy curriculum sequenced around each user's demonstrated weak spots",
      "Embeddable verification widget for newsroom comment sections",
      "Scam-alert integration with banks' transaction-warning flows",
    ],
  },
]

const SCALABILITY = [
  {
    icon: Server,
    title: "Technical scalability",
    body: "Most incoming claims are near-duplicates of something already verified, so they are answered from the verified-claims cache. Only genuinely novel or ambiguous content runs the full pipeline, which keeps the cost of each additional user low.",
  },
  {
    icon: Globe2,
    title: "Regional scalability",
    body: "The multilingual architecture is a natural base for Malaysia, Indonesia and other ASEAN markets facing the same messaging-app-driven misinformation, without rebuilding the core.",
  },
  {
    icon: Banknote,
    title: "Financial sustainability",
    body: "Core verification stays free for individuals, always. A paid enterprise tier for the educator and employer dashboard, together with grant and partnership funding, supports the public-good function.",
  },
]

export function Roadmap() {
  return (
    <section id="roadmap" className="border-b border-border bg-background py-16 lg:py-24">
      <div className="container">
        <SectionHeading
          eyebrow="Roadmap"
          title="Where TrustLens is today, and where it goes next"
          description="We build one boundary at a time and only claim what is actually working. Here is the honest state of each phase."
        />

        <ol className="mt-12 space-y-8 border-l-2 border-border pl-6 sm:pl-10">
          {PHASES.map((phase) => (
            <li key={phase.phase} className="relative">
              <span
                aria-hidden="true"
                className="absolute -left-[calc(1.5rem+9px)] top-1.5 flex h-4 w-4 items-center justify-center rounded-full border-2 border-primary bg-background sm:-left-[calc(2.5rem+9px)]"
              >
                <CircleDot className="h-2.5 w-2.5 text-primary" />
              </span>

              <div className="rounded-lg border border-border bg-muted p-6 lg:p-8">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="text-sm font-semibold uppercase tracking-[0.14em] text-primary">
                    {phase.phase}
                  </p>
                  <Badge variant={STATUS_VARIANT[phase.status]}>{phase.status}</Badge>
                </div>

                <h3 className="mt-3 text-2xl font-bold leading-snug tracking-tight text-foreground">
                  {phase.title}
                </h3>
                <p className="mt-3 max-w-3xl text-base leading-relaxed text-muted-foreground">
                  {phase.summary}
                </p>

                <ul className="mt-5 grid gap-3 lg:grid-cols-2">
                  {phase.items.map((item) => (
                    <li
                      key={item}
                      className="flex items-start gap-3 rounded-md border border-border bg-background p-4"
                    >
                      <span
                        aria-hidden="true"
                        className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
                      />
                      <span className="text-base leading-relaxed text-foreground">
                        {item}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </li>
          ))}
        </ol>

        <div className="mt-16">
          <h3 className="text-2xl font-bold tracking-tight text-foreground">
            Built to grow without breaking
          </h3>
          <div className="mt-6 grid gap-6 lg:grid-cols-3">
            {SCALABILITY.map((item) => (
              <div
                key={item.title}
                className="rounded-lg border border-border bg-background p-6"
              >
                <span className="flex h-12 w-12 items-center justify-center rounded-md bg-primary">
                  <item.icon aria-hidden="true" className="h-6 w-6 text-primary-foreground" />
                </span>
                <h4 className="mt-4 text-xl font-semibold tracking-tight text-foreground">
                  {item.title}
                </h4>
                <p className="mt-3 text-base leading-relaxed text-muted-foreground">
                  {item.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
