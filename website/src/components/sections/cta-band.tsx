import { MessageSquare, Timer, WalletCards } from "lucide-react"

import { TelegramButton } from "@/components/telegram-button"
import { TELEGRAM_BOT_HANDLE } from "@/lib/utils"

const POINTS = [
  { icon: WalletCards, text: "Free to use" },
  { icon: MessageSquare, text: "Works inside Telegram" },
  { icon: Timer, text: "About 30 seconds per check" },
]

export function CtaBand() {
  return (
    <section id="get-started" className="bg-primary py-16 lg:py-20">
      <div className="container">
        <div className="max-w-3xl">
          <h2 className="text-balance text-3xl font-bold leading-tight tracking-tight text-primary-foreground sm:text-4xl">
            The next suspicious forward: send it here first.
          </h2>
          <p className="mt-4 text-pretty text-lg leading-relaxed text-primary-foreground/85">
            Open Telegram, start a chat with{" "}
            <span className="font-semibold text-primary-foreground">
              {TELEGRAM_BOT_HANDLE}
            </span>
            , and forward the message. You will have an answer, with its
            sources, before you have finished your coffee.
          </p>

          <div className="mt-8">
            <TelegramButton
              variant="secondary"
              className="bg-background text-primary hover:bg-background/90"
            />
          </div>

          <ul className="mt-8 flex flex-wrap gap-x-8 gap-y-3">
            {POINTS.map((point) => (
              <li
                key={point.text}
                className="flex items-center gap-2 text-base font-medium text-primary-foreground/90"
              >
                <point.icon aria-hidden="true" className="h-5 w-5" />
                {point.text}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
