import { Eye, FileCheck2, Lock, MapPin, Trash2, UserCheck } from "lucide-react"

import { SectionHeading } from "@/components/section-heading"

const COMMITMENTS = [
  {
    icon: MapPin,
    title: "Kept in Singapore",
    body: "Processing and storage sit on Singapore-region cloud infrastructure, built to comply with the Personal Data Protection Act.",
  },
  {
    icon: Lock,
    title: "Encrypted throughout",
    body: "Everything you send is encrypted in transit and at rest, from the moment it leaves your chat to the moment it is discarded.",
  },
  {
    icon: Trash2,
    title: "Discarded after the check",
    body: "Message content is deleted once the verification is complete, unless you explicitly choose to contribute it to the community review layer.",
  },
  {
    icon: FileCheck2,
    title: "A reviewed source list",
    body: "Search results are checked against a version-controlled list of approved domains before any evidence reaches the model. A lookalike domain is rejected, not trusted.",
  },
  {
    icon: Eye,
    title: "No invented sources",
    body: "The model only sees evidence the system retrieved and validated, and answers using numbered references back to it. It does not browse freely or answer from memory.",
  },
  {
    icon: UserCheck,
    title: "A human in the loop",
    body: "Low-confidence and genuinely ambiguous cases are routed to human fact-checker review, and that feedback is used to correct the system.",
  },
]

export function Governance() {
  return (
    <section id="trust" className="border-b border-border bg-muted py-16 lg:py-24">
      <div className="container">
        <SectionHeading
          eyebrow="Trust and data handling"
          title="What happens to the message you send us"
          description="Asking people to forward private messages to a bot is asking for trust. These are the rules we hold ourselves to, stated plainly."
        />

        <div className="mt-12 grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {COMMITMENTS.map((item) => (
            <div key={item.title} className="bg-background p-6">
              <item.icon aria-hidden="true" className="h-6 w-6 text-primary" />
              <h3 className="mt-4 text-lg font-semibold tracking-tight text-foreground">
                {item.title}
              </h3>
              <p className="mt-2 text-base leading-relaxed text-muted-foreground">
                {item.body}
              </p>
            </div>
          ))}
        </div>

        <p className="mt-8 max-w-3xl text-base leading-relaxed text-muted-foreground">
          TrustLens SG is a decision aid, not an authority. It is designed to
          complement Singapore&rsquo;s existing fact-checking and reporting
          bodies, never to replace them. For matters requiring an official
          determination, refer to the responsible government agency.
        </p>
      </div>
    </section>
  )
}
