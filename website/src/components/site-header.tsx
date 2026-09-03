import { useState } from "react"
import { Info, Menu, ScanEye, X } from "lucide-react"

import { TelegramButton } from "@/components/telegram-button"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const NAV_LINKS = [
  { href: "#problem", label: "The problem" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#features", label: "Features" },
  { href: "#roadmap", label: "Roadmap" },
  { href: "#faq", label: "Questions" },
]

export function SiteHeader() {
  const [open, setOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background">
      {/* Advisory bar: states plainly what this site is, in the manner of an
          official notice, without claiming government status. */}
      <div className="border-b border-border bg-muted">
        <div className="container flex items-center gap-2 py-2">
          <Info aria-hidden="true" className="h-4 w-4 shrink-0 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            An independent student-led project from Singapore Management
            University. Not a government agency or official government service.
          </p>
        </div>
      </div>

      <div className="container flex h-20 items-center justify-between gap-6">
        <a
          href="#top"
          className="flex items-center gap-3 rounded-md"
          aria-label="TrustLens SG, back to top"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-md bg-primary">
            <ScanEye aria-hidden="true" className="h-6 w-6 text-primary-foreground" />
          </span>
          <span className="leading-tight">
            <span className="block text-xl font-bold tracking-tight text-foreground">
              TrustLens<span className="text-primary"> SG</span>
            </span>
            <span className="block text-xs font-medium uppercase tracking-[0.12em] text-muted-foreground">
              Check before you forward
            </span>
          </span>
        </a>

        <nav aria-label="Main" className="hidden lg:block">
          <ul className="flex items-center gap-1">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  className="rounded-md px-3 py-2 text-base font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-primary"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="hidden lg:block">
          <TelegramButton size="default" label="Open the Telegram bot" />
        </div>

        <Button
          variant="outline"
          size="icon"
          className="lg:hidden"
          aria-expanded={open}
          aria-controls="mobile-navigation"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? (
            <X aria-hidden="true" className="h-5 w-5" />
          ) : (
            <Menu aria-hidden="true" className="h-5 w-5" />
          )}
        </Button>
      </div>

      <div
        id="mobile-navigation"
        className={cn("border-t border-border bg-background lg:hidden", !open && "hidden")}
      >
        <nav aria-label="Main, mobile" className="container py-4">
          <ul className="flex flex-col">
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  onClick={() => setOpen(false)}
                  className="block rounded-md px-2 py-3 text-lg font-medium text-foreground transition-colors hover:bg-secondary"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
          <TelegramButton className="mt-4 w-full" label="Open the Telegram bot" />
        </nav>
      </div>
    </header>
  )
}
