import { cn } from "@/lib/utils"

interface SectionHeadingProps {
  eyebrow: string
  title: string
  description?: string
  className?: string
  align?: "left" | "center"
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  className,
  align = "left",
}: SectionHeadingProps) {
  return (
    <div
      className={cn(
        "max-w-3xl",
        align === "center" && "mx-auto text-center",
        className,
      )}
    >
      <p className="text-sm font-semibold uppercase tracking-[0.14em] text-primary">
        {eyebrow}
      </p>
      <h2 className="mt-3 text-pretty text-3xl font-bold leading-tight tracking-tight text-foreground sm:text-4xl">
        {title}
      </h2>
      {description ? (
        <p className="mt-4 text-pretty text-lg leading-relaxed text-muted-foreground">
          {description}
        </p>
      ) : null}
    </div>
  )
}
