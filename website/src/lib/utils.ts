import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Single source of truth for the Telegram bot handle. */
export const TELEGRAM_BOT_HANDLE = "@TrustLensBotBot"
export const TELEGRAM_BOT_URL = "https://t.me/TrustLensBotBot"
