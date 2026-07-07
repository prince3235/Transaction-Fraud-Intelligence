import { cn } from "@/lib/utils"
import React from "react"

export interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  as?: React.ElementType
}

export function GlassPanel({ className, as: Component = "div", ...props }: GlassPanelProps) {
  return (
    <Component
      className={cn(
        "bg-foam backdrop-blur-md border border-mist/10 rounded-xl",
        className
      )}
      {...props}
    />
  )
}
