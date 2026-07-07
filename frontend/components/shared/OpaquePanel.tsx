import { cn } from "@/lib/utils"
import React from "react"

export interface OpaquePanelProps extends React.HTMLAttributes<HTMLDivElement> {
  as?: React.ElementType
}

export function OpaquePanel({ className, as: Component = "div", ...props }: OpaquePanelProps) {
  return (
    <Component
      className={cn(
        "bg-frost border border-ink/12 rounded-sm shadow-[0_1px_3px_rgba(58,34,26,0.08)]",
        className
      )}
      {...props}
    />
  )
}
