import { Gauge, Target, TrendingUp, Users } from "lucide-react"

import { SectionHeading } from "@/components/section-heading"

const OUTCOMES = [
  {
    icon: Users,
    title: "Fewer people forward without checking",
    body: "The aim is behavioural, not clerical. Making verification effortless narrows the gap between how accurate people think they are and how accurate they actually are.",
  },
  {
    icon: TrendingUp,
    title: "Slower spread of scams and manipulated media",
    body: "Every check that ends in a correction shared back to a group removes one link from the forwarding chain, at the point where that chain is cheapest to break.",
  },
  {
    icon: Gauge,
    title: "Less pressure on reactive enforcement",
    body: "A widely used verification layer inside messaging apps reduces the volume of harmful content that has to be addressed after the fact, through formal correction directions or safety cases.",
  },
  {
    icon: Target,
    title: "Steadier public trust when it matters most",
    body: "Misinformation spikes during elections, health emergencies and economic shocks. A familiar, source-citing check helps people hold their footing in exactly those moments.",
  },
]

const KPIS = [
  {
    kpi: "Adoption",
    measures: "Active users reached and messages verified each month",
    target: "50,000 active users and 200,000 verifications within 12 months of launch",
  },
  {
    kpi: "Response speed",
    measures: "Median time from forward to verdict delivered",
    target: "Under 30 seconds for cached and common claims",
  },
  {
    kpi: "Verdict accuracy",
    measures: "Precision and recall against an expert-labelled test set",
    target: "Over 90% agreement with fact-checker adjudication",
  },
  {
    kpi: "Behaviour change",
    measures: "Self-reported forwarding behaviour before and after use",
    target: "At least 30% of users report pausing to verify, within 6 months",
  },
  {
    kpi: "Literacy uplift",
    measures: "Quiz scores before and after, across national digital skills competencies",
    target: "Average 20% score improvement after 10 interactions",
  },
  {
    kpi: "Priority segments",
    measures: "Share of active users aged 40 to 65 and 13 to 24",
    target: "At least 60% of active users from the two target groups",
  },
]

export function Impact() {
  return (
    <section id="impact" className="border-b border-border bg-muted py-16 lg:py-24">
      <div className="container">
        <SectionHeading
          eyebrow="Intended impact"
          title="Designed to change behaviour, not just return an answer"
          description="A correct verdict that nobody acts on is worth very little. These are the outcomes we hold ourselves to, and the numbers we will measure them by."
        />

        <div className="mt-12 grid gap-6 sm:grid-cols-2">
          {OUTCOMES.map((outcome) => (
            <div
              key={outcome.title}
              className="rounded-lg border border-border bg-background p-6"
            >
              <outcome.icon aria-hidden="true" className="h-7 w-7 text-primary" />
              <h3 className="mt-4 text-xl font-semibold leading-snug tracking-tight text-foreground">
                {outcome.title}
              </h3>
              <p className="mt-3 text-base leading-relaxed text-muted-foreground">
                {outcome.body}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-14">
          <h3 className="text-2xl font-bold tracking-tight text-foreground">
            How we will measure success
          </h3>
          <p className="mt-3 max-w-3xl text-base leading-relaxed text-muted-foreground">
            Targets are set for the first twelve months after public launch.
          </p>

          <div className="mt-6 overflow-x-auto rounded-lg border border-border bg-background">
            <table className="w-full min-w-[46rem] border-collapse text-left">
              <caption className="sr-only">
                Key performance indicators and twelve-month targets
              </caption>
              <thead>
                <tr className="border-b border-border bg-secondary">
                  <th scope="col" className="px-6 py-4 text-base font-semibold text-foreground">
                    Indicator
                  </th>
                  <th scope="col" className="px-6 py-4 text-base font-semibold text-foreground">
                    What it measures
                  </th>
                  <th scope="col" className="px-6 py-4 text-base font-semibold text-foreground">
                    Twelve-month target
                  </th>
                </tr>
              </thead>
              <tbody>
                {KPIS.map((row) => (
                  <tr key={row.kpi} className="border-b border-border last:border-b-0">
                    <th
                      scope="row"
                      className="px-6 py-4 align-top text-base font-semibold text-foreground"
                    >
                      {row.kpi}
                    </th>
                    <td className="px-6 py-4 align-top text-base text-muted-foreground">
                      {row.measures}
                    </td>
                    <td className="px-6 py-4 align-top text-base text-foreground">
                      {row.target}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  )
}
