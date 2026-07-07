import { OpaquePanel } from "./OpaquePanel";
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
    <OpaquePanel className={cn("p-4 flex flex-col justify-between h-full min-w-[200px]", className)}>
      <div className="flex justify-between items-start mb-2">
        <span className="text-[12px] font-sans text-mist/70 tracking-wide uppercase">
          {label}
        </span>
        {trend !== undefined && (
          <span
            className={cn(
              "text-[10px] font-mono px-1.5 py-0.5 rounded-sm flex items-center",
              isDanger 
                ? "bg-ember/20 text-text-on-ember"
                : isPositiveTrend 
                  ? "bg-signal/20 text-signal" 
                  : isNegativeTrend 
                    ? "bg-ember/20 text-ember" 
                    : "bg-mist/10 text-mist"
            )}
          >
            {trend > 0 ? "+" : ""}{trend}%
          </span>
        )}
      </div>
      <div className={cn("font-display text-[24px] font-medium leading-none", isDanger ? "text-ember" : "text-mist")}>
        {value}
      </div>
    </OpaquePanel>
  );
}
