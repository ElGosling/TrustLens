import {
  Chrome,
  Flag,
  GraduationCap,
  LayoutDashboard,
  Network,
  ScanFace,
  Send,
  ShieldAlert,
} from "lucide-react"

import { SectionHeading } from "@/components/section-heading"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

type Status = "Available now" | "In development" | "Planned"

const STATUS_VARIANT: Record<Status, "success" | "warning" | "outline"> = {
  "Available now": "success",
  "In development": "warning",
  Planned: "outline",
}

interface Feature {
  icon: typeof Send
  title: string
  status: Status
  does: string
  protects: string
}

const FEATURES: Feature[] = [
  {
    icon: Send,
    title: "Forward-to-verify bot",
    status: "Available now",
    does: "Forward any suspicious message or link to the bot on Telegram. It replies in the same chat with a verdict, a confidence level, a short explanation and the source links, formatted as a card you can forward onward.",
    protects:
      "Turns the moment of doubt into a single, low-effort action. Instead of quietly passing a message on, you can send a correction back to the group just as easily as you would have forwarded the original.",
  },
  {
    icon: Network,
    title: "Explainable verification engine",
    status: "Available now",
    does: "Verdicts are never a single opaque model answer. The system extracts the claim, searches only a reviewed list of trusted domains, and asks the model to reason strictly over the evidence it retrieved, citing which source supports which point.",
    protects:
      "Removes the two biggest failure modes of AI answers: invented sources and confident guessing. If no approved source covers the claim, the reply is Unverified rather than a plausible-sounding fabrication.",
  },
  {
    icon: ScanFace,
    title: "Image, video and voice forensics",
    status: "In development",
    does: "Reverse-image search, deepfake detection and voice-clone analysis for forwarded media, alongside a link inspector that safely opens a forwarded URL to judge what the site actually is.",
    protects:
      "Directly addresses the fastest-growing scam category, including cloned voices of family members asking for money, which almost no consumer tool currently checks.",
  },
  {
    icon: GraduationCap,
    title: "Micro-literacy recap quiz",
    status: "Available now",
    does: "Send /quiz and the bot builds a short recap from what you personally checked: it replays your own claims and asks what the verdict was, then drills the specific techniques you ran into, such as an out-of-context photo or a manipulated statistic. /stats shows your accuracy and daily streak.",
    protects:
      "Builds lasting judgement instead of dependence on the bot. Over time users recognise the pattern before they even forward it for checking.",
  },
  {
    icon: ShieldAlert,
    title: "Automatic escalation for real harm",
    status: "Planned",
    does: "When the engine detects a likely scam or clear harm rather than a merely inaccurate claim, TrustLens can lodge a report with the relevant national channel on the user's behalf, after independently inspecting the destination link.",
    protects:
      "Cuts the delay between one person noticing a scam and the authorities being told about it, and removes the reporting burden from the user entirely.",
  },
  {
    icon: Chrome,
    title: "Browser and social feed badges",
    status: "Planned",
    does: "A browser extension places a small credibility badge on posts in social feeds and comment sections. Hovering it reveals the same explainable verdict the bot gives.",
    protects:
      "Extends protection from private chats to open feeds, so misinformation is flagged while scrolling, without the user having to ask.",
  },
  {
    icon: Flag,
    title: "Community trust layer",
    status: "Planned",
    does: "Users can flag suspicious content, vote on genuinely ambiguous cases, and submit corrections. Consistently accurate contributors earn recognition.",
    protects:
      "Surfaces emerging local claims that no fact-checker has written about yet, and converts passive bystanders into an early-warning network.",
  },
  {
    icon: LayoutDashboard,
    title: "Educator and employer dashboard",
    status: "Planned",
    does: "Schools, community clubs and employers running digital literacy sessions see aggregate, privacy-preserving statistics for their cohort: completion rates, the fallacies most often met, and improvement over time.",
    protects:
      "Lets programme organisers see whether their workshops actually changed behaviour, and target follow-up sessions at the weaknesses that remain.",
  },
]

export function Features() {
  return (
    <section id="features" className="border-b border-border bg-background py-16 lg:py-24">
      <div className="container">
        <SectionHeading
          eyebrow="Main features"
          title="What TrustLens does, and how each part reduces risk"
          description="Each feature exists to close one of the five gaps. Where something is still being built, we say so plainly."
        />

        <div className="mt-12 grid gap-6 lg:grid-cols-2">
          {FEATURES.map((feature) => (
            <Card key={feature.title} className="flex h-full flex-col">
              <CardHeader className="space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md border border-border bg-secondary">
                    <feature.icon aria-hidden="true" className="h-6 w-6 text-primary" />
                  </span>
                  <Badge variant={STATUS_VARIANT[feature.status]}>
                    {feature.status}
                  </Badge>
                </div>
                <CardTitle>{feature.title}</CardTitle>
              </CardHeader>

              <CardContent className="flex flex-1 flex-col gap-4">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                    What it does
                  </p>
                  <p className="mt-1.5 text-base leading-relaxed text-foreground">
                    {feature.does}
                  </p>
                </div>
                <div className="border-t border-border pt-4">
                  <p className="text-sm font-semibold uppercase tracking-[0.12em] text-primary">
                    How it protects you
                  </p>
                  <p className="mt-1.5 text-base leading-relaxed text-muted-foreground">
                    {feature.protects}
                  </p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
