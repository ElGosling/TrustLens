import { GraduationCap, MapPin, MessageCircle, Quote, Scale } from "lucide-react"

import { SectionHeading } from "@/components/section-heading"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const PRINCIPLES = [
  {
    icon: MessageCircle,
    title: "Go to where the message already is",
    body: "We do not ask anyone to download a new app or learn a new habit. The check happens inside Telegram and WhatsApp, in the same chat window where the forward arrived.",
  },
  {
    icon: Scale,
    title: "Show the reasoning, not just the answer",
    body: "Every verdict names the sources it relied on and states how confident it is. Replacing one unexplained claim with another unexplained claim helps nobody.",
  },
  {
    icon: GraduationCap,
    title: "Teach a little with every check",
    body: "Each check quietly builds skill. At the end of the week the bot turns the specific tricks you encountered into a short recap, so the next fake is easier to spot unaided.",
  },
  {
    icon: MapPin,
    title: "Built for Singapore, in Singapore",
    body: "Support for all four official languages, Singlish-aware reading of messages, a voice-first mode for seniors, and processing kept on Singapore-region infrastructure.",
  },
]

const PERSONAS = [
  {
    name: "Mdm Tan, 58",
    role: "Retail supervisor, grandmother of two",
    quote:
      "My chat group sends so many messages every day. I don't want to be the one who spreads something wrong, but I also don't have time to check every link.",
    needs: "A fast, no-download way to check a message before forwarding it, in simple English or Mandarin.",
  },
  {
    name: "Nadia, 17",
    role: "Junior college student",
    quote:
      "I see so much stuff on TikTok that looks real but feels off. I don't want to fact-check every video manually.",
    needs: "Credibility signals while scrolling, and short explanations she can show friends.",
  },
  {
    name: "Mr Rajan, 44",
    role: "Community club programme coordinator",
    quote:
      "We run digital literacy talks, but I have no way to know if they're actually changing behaviour once people go home.",
    needs: "A way to measure whether workshop attendees apply what they learned.",
  },
]

export function Rationale() {
  return (
    <section id="rationale" className="border-b border-border bg-background py-16 lg:py-24">
      <div className="container">
        <SectionHeading
          eyebrow="Our rationale"
          title="Why we built TrustLens the way we did"
          description="TrustLens SG adds a small, trustworthy checking layer at the exact moment someone decides whether to believe a message or pass it on. Four decisions shaped the whole design."
        />

        <div className="mt-12 grid gap-6 sm:grid-cols-2">
          {PRINCIPLES.map((principle) => (
            <Card key={principle.title} className="h-full bg-muted">
              <CardHeader>
                <span className="flex h-12 w-12 items-center justify-center rounded-md bg-primary">
                  <principle.icon
                    aria-hidden="true"
                    className="h-6 w-6 text-primary-foreground"
                  />
                </span>
                <CardTitle>{principle.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-base leading-relaxed text-muted-foreground">
                  {principle.body}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="mt-16">
          <h3 className="text-2xl font-bold tracking-tight text-foreground">
            Who we built it for
          </h3>
          <p className="mt-3 max-w-3xl text-lg leading-relaxed text-muted-foreground">
            Our first priority is adults aged 40 to 65, the parents and
            grandparents who forward most actively and carry the most real-world
            risk from a scam. The same tool serves younger users and the
            community organisations that run digital literacy programmes.
          </p>

          <div className="mt-8 grid gap-6 lg:grid-cols-3">
            {PERSONAS.map((persona) => (
              <Card key={persona.name} className="h-full">
                <CardHeader className="space-y-1">
                  <CardTitle>{persona.name}</CardTitle>
                  <p className="text-base text-muted-foreground">{persona.role}</p>
                </CardHeader>
                <CardContent>
                  <blockquote className="border-l-2 border-primary pl-4">
                    <Quote
                      aria-hidden="true"
                      className="mb-2 h-5 w-5 text-muted-foreground"
                    />
                    <p className="text-base italic leading-relaxed text-foreground">
                      {persona.quote}
                    </p>
                  </blockquote>
                  <p className="mt-4 text-base leading-relaxed text-muted-foreground">
                    <span className="font-semibold text-foreground">Needs: </span>
                    {persona.needs}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
