import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  trend?: number;
  tone?: 'default' | 'danger';
  className?: string;
}

export function StatCard({ label, value, trend, tone = 'default', className }: StatCardProps) {
  const isDanger = tone === 'danger';
  const isPositiveTrend = trend !== undefined && trend > 0;
  const isNegativeTrend = trend !== undefined && trend < 0;

  return (
    <div className={cn("p-4 flex flex-col justify-between h-full min-w-[200px] bg-frost border border-ink/12 rounded-sm shadow-[0_1px_3px_rgba(58,34,26,0.08)]", className)}>
      <div className="flex justify-between items-start mb-2">
        <span className="text-[12px] font-sans text-ink/65 tracking-wide uppercase">
          {label}
        </span>
        {trend !== undefined && (
          <span
            className={cn(
              "text-[10px] font-mono px-1.5 py-0.5 rounded-sm flex items-center",
              isDanger 
                ? "bg-rust/20 text-rust"
                : isPositiveTrend 
                  ? "bg-ink/10 text-ink" 
                  : isNegativeTrend 
                    ? "bg-rust/10 text-rust" 
                    : "bg-ink/10 text-ink"
            )}
          >
            {trend > 0 ? "+" : ""}{trend}%
          </span>
        )}
      </div>
      <div className={cn("font-display text-[28px] font-medium leading-none text-ink")}>
        {value}
      </div>
    </div>
  );
}
