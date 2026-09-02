import { ArrowRight, CheckCircle2, Clock, Languages, Link2, ShieldCheck, XCircle } from "lucide-react"

import { TelegramButton } from "@/components/telegram-button"
import { Button } from "@/components/ui/button"
import { TELEGRAM_BOT_HANDLE } from "@/lib/utils"

const ASSURANCES = [
  { icon: Clock, label: "A verdict in about 30 seconds" },
  { icon: Link2, label: "Every answer cites its sources" },
  { icon: Languages, label: "Plain language, no jargon" },
  { icon: ShieldCheck, label: "Free to use. No app to install." },
]

export function Hero() {
  return (
    <section id="top" className="border-b border-border bg-background">
      <div className="container grid gap-14 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-24">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full border border-border bg-muted px-4 py-1.5 text-sm font-semibold text-primary">
            <ShieldCheck aria-hidden="true" className="h-4 w-4" />
            Fact-checking inside the apps you already use
          </p>

          <h1 className="mt-6 text-balance text-4xl font-bold leading-[1.1] tracking-tight text-foreground sm:text-5xl lg:text-[3.4rem]">
            Not sure if a message is true? Forward it to us first.
          </h1>

          <p className="mt-6 max-w-xl text-pretty text-xl leading-relaxed text-muted-foreground">
            TrustLens SG checks suspicious messages, links, photos and voice
            notes for you. Send it to our Telegram bot and you will get a clear
            verdict, a short explanation, and links to the original trusted
            sources, so you can decide whether to forward it on.
          </p>

          <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center">
            <TelegramButton />
            <Button asChild variant="outline" size="lg">
              <a href="#how-it-works">
                See how it works
                <ArrowRight aria-hidden="true" className="h-5 w-5" />
              </a>
            </Button>
          </div>

          <p className="mt-4 text-base text-muted-foreground">
            Opens Telegram and starts a chat with{" "}
            <span className="font-semibold text-foreground">
              {TELEGRAM_BOT_HANDLE}
            </span>
            .
          </p>

          <ul className="mt-10 grid gap-x-8 gap-y-4 sm:grid-cols-2">
            {ASSURANCES.map((item) => (
              <li key={item.label} className="flex items-start gap-3">
                <item.icon
                  aria-hidden="true"
                  className="mt-0.5 h-5 w-5 shrink-0 text-primary"
                />
                <span className="text-base font-medium text-foreground">
                  {item.label}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Illustrative example of a reply from the bot. */}
        <div className="lg:pl-6">
          <figure className="rounded-lg border border-border bg-muted p-4 sm:p-6">
            <figcaption className="mb-4 text-sm font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              Example of a reply
            </figcaption>

            <div className="rounded-md border border-border bg-background p-4">
              <p className="text-sm font-semibold text-muted-foreground">
                You forwarded
              </p>
              <p className="mt-2 text-base leading-relaxed text-foreground">
                &ldquo;URGENT!! Please share to all family. The new vaccine
                batch has been recalled nationwide after 3 deaths. Government
                is not telling us.&rdquo;
              </p>
            </div>

            <div className="mt-4 overflow-hidden rounded-md border border-border bg-background">
              <div className="flex items-center gap-2 bg-red-700 px-4 py-3">
                <XCircle aria-hidden="true" className="h-5 w-5 text-white" />
                <p className="text-lg font-bold text-white">False</p>
                <p className="ml-auto text-sm font-semibold text-white/90">
                  Confidence: High
                </p>
              </div>

              <div className="space-y-4 p-4">
                <p className="text-base leading-relaxed text-foreground">
                  No vaccine batch recall has been announced. The health
                  authority&rsquo;s latest advisory, published this week, lists
                  all batches as in use, and no newsroom has reported a recall.
                </p>

                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                    Checked against
                  </p>
                  <ul className="mt-2 space-y-1.5">
                    {[
                      "Health authority advisory (official)",
                      "National newswire fact-check desk",
                      "International fact-check database",
                    ].map((source) => (
                      <li
                        key={source}
                        className="flex items-start gap-2 text-base text-foreground"
                      >
                        <CheckCircle2
                          aria-hidden="true"
                          className="mt-1 h-4 w-4 shrink-0 text-emerald-700"
                        />
                        <span className="underline decoration-border underline-offset-4">
                          {source}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>

                <p className="border-t border-border pt-3 text-sm text-muted-foreground">
                  Checked by TrustLens SG. Tap to share this card back to the
                  group.
                </p>
              </div>
            </div>

            <p className="mt-4 text-sm text-muted-foreground">
              Illustration only. Wording and sources shown are an example of the
              format, not a real check.
            </p>
          </figure>
        </div>
      </div>
    </section>
  )
}
