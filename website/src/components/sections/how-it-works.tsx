import {
  AlertTriangle,
  CheckCircle2,
  Forward,
  HelpCircle,
  Search,
  Share2,
  Smile,
  Sparkles,
  XCircle,
} from "lucide-react"

import { SectionHeading } from "@/components/section-heading"
import { TelegramButton } from "@/components/telegram-button"

const STEPS = [
  {
    icon: Forward,
    title: "Forward the message",
    body: "Send the text, link, photo, video or voice note to the TrustLens bot on Telegram. Nothing to install, no form to fill in. If you are unsure what to ask, just add \u201cIs this true?\u201d",
  },
  {
    icon: Search,
    title: "We find the actual claim",
    body: "The bot reads the message and pulls out the specific factual claim being made, separating it from the alarm, the emojis and the forwarding chain.",
  },
  {
    icon: Sparkles,
    title: "We check it against trusted sources only",
    body: "The claim is cross-checked against government feeds, established newsrooms and fact-check databases on a reviewed list. If no approved source covers it, the bot says so rather than guessing.",
  },
  {
    icon: Share2,
    title: "You get a verdict you can share",
    body: "A verdict, a confidence level, a two-sentence explanation and the source links come back in roughly 30 seconds, formatted as a card you can forward straight into the group where the claim appeared.",
  },
]

const VERDICTS = [
  {
    icon: CheckCircle2,
    label: "True",
    meaning: "Trusted sources confirm the claim.",
    className: "border-emerald-200 bg-emerald-50 text-emerald-900",
    iconClassName: "text-emerald-700",
  },
  {
    icon: XCircle,
    label: "False",
    meaning: "Trusted sources contradict the claim.",
    className: "border-red-200 bg-red-50 text-red-900",
    iconClassName: "text-red-700",
  },
  {
    icon: AlertTriangle,
    label: "Misleading",
    meaning: "Partly accurate, but framed to mislead.",
    className: "border-amber-200 bg-amber-50 text-amber-900",
    iconClassName: "text-amber-700",
  },
  {
    icon: Smile,
    label: "Satire",
    meaning: "Written as humour, not as news.",
    className: "border-sky-200 bg-sky-50 text-sky-900",
    iconClassName: "text-sky-700",
  },
  {
    icon: HelpCircle,
    label: "Unverified",
    meaning: "No trusted source covers it yet. Treat with caution.",
    className: "border-border bg-muted text-foreground",
    iconClassName: "text-muted-foreground",
  },
]

export function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="border-b border-border bg-muted py-16 lg:py-24"
    >
      <div className="container">
        <SectionHeading
          eyebrow="How it works"
          title="Four steps, about thirty seconds"
          description="You do one thing: forward the message. TrustLens does the rest and shows its working."
        />

        <ol className="mt-12 grid gap-6 lg:grid-cols-4">
          {STEPS.map((step, index) => (
            <li
              key={step.title}
              className="relative flex h-full flex-col rounded-lg border border-border bg-background p-6"
            >
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-lg font-bold text-primary-foreground">
                  {index + 1}
                </span>
                <step.icon aria-hidden="true" className="h-6 w-6 text-primary" />
              </div>
              <h3 className="mt-4 text-xl font-semibold leading-snug tracking-tight text-foreground">
                {step.title}
              </h3>
              <p className="mt-3 text-base leading-relaxed text-muted-foreground">
                {step.body}
              </p>
            </li>
          ))}
        </ol>

        <div className="mt-14 rounded-lg border border-border bg-background p-6 lg:p-8">
          <h3 className="text-2xl font-bold tracking-tight text-foreground">
            What the five verdicts mean
          </h3>
          <p className="mt-3 max-w-3xl text-base leading-relaxed text-muted-foreground">
            Every reply uses the same five labels and the same colours, so the
            card is recognisable at a glance, even to someone who has never used
            TrustLens before.
          </p>

          <dl className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            {VERDICTS.map((verdict) => (
              <div
                key={verdict.label}
                className={`rounded-md border p-4 ${verdict.className}`}
              >
                <dt className="flex items-center gap-2 text-lg font-bold">
                  <verdict.icon
                    aria-hidden="true"
                    className={`h-5 w-5 ${verdict.iconClassName}`}
                  />
                  {verdict.label}
                </dt>
                <dd className="mt-2 text-base leading-relaxed">
                  {verdict.meaning}
                </dd>
              </div>
            ))}
          </dl>

          <div className="mt-8 border-t border-border pt-6">
            <TelegramButton label="Try it now on Telegram" />
          </div>
        </div>
      </div>
    </section>
  )
}
