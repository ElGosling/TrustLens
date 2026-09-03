import { Send } from "lucide-react"

import { Button, type ButtonProps } from "@/components/ui/button"
import { TELEGRAM_BOT_URL, cn } from "@/lib/utils"

interface TelegramButtonProps extends Omit<ButtonProps, "asChild"> {
  label?: string
}

/**
 * Primary call to action. Always opens the live Telegram bot in a new tab.
 */
export function TelegramButton({
  label = "Open the TrustLens bot on Telegram",
  className,
  size = "lg",
  variant = "default",
  ...props
}: TelegramButtonProps) {
  return (
    <Button asChild size={size} variant={variant} className={cn(className)} {...props}>
      <a href={TELEGRAM_BOT_URL} target="_blank" rel="noopener noreferrer">
        <Send aria-hidden="true" className="h-5 w-5" />
        {label}
      </a>
    </Button>
  )
}
