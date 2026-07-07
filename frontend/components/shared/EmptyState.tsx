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
    <div className={cn("flex flex-col items-center justify-center p-12 text-center border border-dashed border-ink/20 rounded-sm bg-frost shadow-[0_1px_3px_rgba(58,34,26,0.08)]", className)}>
      {icon && <div className="mb-4 text-ink/40">{icon}</div>}
      <h3 className="mb-1 text-lg font-display font-medium text-ink">{title}</h3>
      <p className="mb-6 text-sm font-sans text-ink/70 max-w-sm">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
}
