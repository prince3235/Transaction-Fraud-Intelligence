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
    high: 'bg-ember text-[var(--text-on-ember)]',
    medium: 'bg-signal text-[var(--text-on-signal)]',
    low: 'bg-mist text-trench'
  };

  const label = level.charAt(0).toUpperCase() + level.slice(1);

  return (
    <span
      className={cn(
        "inline-flex items-center justify-center font-medium rounded-full uppercase tracking-wider",
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
