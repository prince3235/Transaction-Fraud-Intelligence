import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center p-12 text-center border border-dashed border-mist/20 rounded-xl bg-trench/50", className)}>
      {icon && <div className="mb-4 text-mist/50">{icon}</div>}
      <h3 className="mb-1 text-lg font-display font-medium text-mist">{title}</h3>
      <p className="mb-6 text-sm font-sans text-mist/70 max-w-sm">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
}
