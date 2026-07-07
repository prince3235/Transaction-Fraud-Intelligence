import { cn } from "@/lib/utils"
import { RiskLevel } from "@/types"

interface RiskBadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  level: RiskLevel;
  size?: 'sm' | 'md' | 'lg';
}

export function RiskBadge({ level, size = 'sm', className, ...props }: RiskBadgeProps) {
  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-1',
    lg: 'text-sm px-3 py-1.5'
  };

  const colorClasses = {
    high: 'bg-rust text-paper',
    medium: 'bg-clay text-paper',
    low: 'bg-amber text-ink'
  };

  const label = level; // handled by uppercase class

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center font-mono font-medium rounded-sm border border-ink/20 uppercase tracking-[0.05em]",
        sizeClasses[size],
        colorClasses[level],
        className
      )}
      {...props}
    >
      {label}
    </span>
  )
}
