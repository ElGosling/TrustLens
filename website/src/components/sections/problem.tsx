import { Brain, EyeOff, Lock, Repeat2, Sparkles } from "lucide-react"

import { SectionHeading } from "@/components/section-heading"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const GAPS = [
  {
    icon: Brain,
    title: "We trust our own judgement too much",
    body: "Most people believe they can spot a fake on sight, so they rarely stop to check. That confidence is exactly what makes a well-written falsehood travel.",
    source: "Ipsos (2025), The Susceptibility of Singaporeans Towards Fake News",
  },
  {
    icon: Lock,
    title: "Chat groups cannot be checked from the outside",
    body: "WhatsApp and Telegram messages are end-to-end encrypted. No platform or fact-checker can see inside a family chat, yet that is where false content spreads most.",
    source: "SUTD, Local Perceptions and Practices of News Sharing and Fake News",
  },
  {
    icon: Repeat2,
    title: "People see something wrong and stay quiet",
    body: "When Singaporeans meet false information, they seldom correct it or report it. Often they simply pass it on, because saying nothing is easier than starting an argument.",
    source: "Institute of Policy Studies (IPS), NUS",
  },
  {
    icon: EyeOff,
    title: "Help sits on websites nobody visits mid-forward",
    body: "Official resources exist and are good. But they are destinations you must remember to go to. They are not present at the moment a suspicious message lands in your hand.",
    source: "Media Literacy Council, factually.gov.sg",
  },
  {
    icon: Sparkles,
    title: "AI has made fakes cheap to produce",
    body: "More than 3,000 AI-generated content farm sites are now tracked across 16 languages, and voice-cloning scams that imitate a relative's voice are growing quickly.",
    source: "NewsGuard AI Tracking Centre, March 2026",
  },
]

const STATS = [
  {
    value: "40 to 65",
    label: "The age group most exposed to forwarded misinformation, and the least served by current programmes",
  },
  {
    value: "3,000+",
    label: "AI-generated content farm sites tracked worldwide across 16 languages, as of March 2026",
  },
  {
    value: "Encrypted",
    label: "Private chat groups cannot be scanned by platforms or fact-checkers, so the check must start with the user",
  },
]

export function Problem() {
  return (
    <section id="problem" className="border-b border-border bg-muted py-16 lg:py-24">
      <div className="container">
        <SectionHeading
          eyebrow="The problem"
          title="Singapore is not short of fact-checkers. It is short of a fact-check that arrives in time."
          description="Official resources exist. Newsroom fact-check desks exist. And yet a false message still reaches a family group faster than a correction ever does. Five gaps explain why."
        />

        <dl className="mt-12 grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-3">
          {STATS.map((stat) => (
            <div key={stat.value} className="bg-background p-6">
              <dt className="text-3xl font-bold tracking-tight text-primary">
                {stat.value}
              </dt>
              <dd className="mt-2 text-base leading-relaxed text-muted-foreground">
                {stat.label}
              </dd>
            </div>
          ))}
        </dl>

        <ol className="mt-10 grid gap-6 lg:grid-cols-2">
          {GAPS.map((gap, index) => (
            <li key={gap.title} className={index === GAPS.length - 1 ? "lg:col-span-2" : undefined}>
              <Card className="h-full">
                <CardHeader className="flex-row items-start gap-4 space-y-0">
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md border border-border bg-secondary">
                    <gap.icon aria-hidden="true" className="h-6 w-6 text-primary" />
                  </span>
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                      Gap {index + 1}
                    </p>
                    <CardTitle className="mt-1">{gap.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-base leading-relaxed text-muted-foreground">
                    {gap.body}
                  </p>
                  <p className="mt-4 border-t border-border pt-3 text-sm text-muted-foreground">
                    Source: {gap.source}
                  </p>
                </CardContent>
              </Card>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
