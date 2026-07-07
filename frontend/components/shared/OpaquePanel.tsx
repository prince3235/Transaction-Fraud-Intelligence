import { cn } from "@/lib/utils"
import React from "react"

export interface OpaquePanelProps extends React.HTMLAttributes<HTMLDivElement> {
  as?: React.ElementType
}

export function OpaquePanel({ className, as: Component = "div", ...props }: OpaquePanelProps) {
  return (
    <Component
      className={cn(
        "bg-trench border border-mist/20 rounded-xl",
        className
      )}
      {...props}
    />
  )
}
