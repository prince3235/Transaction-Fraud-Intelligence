"use client"

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/client"
import { PredictionLog } from "@/types"
import { cn } from "@/lib/utils"
import { useEffect, useState } from "react"

export function LiveTicker() {
  const [mounted, setMounted] = useState(false);
  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.getAlerts(1),
    // Fallback polling is handled here if WS dies, or just general fallback
    refetchInterval: 15000, 
    initialData: []
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return <div className="flex-1 overflow-hidden h-6" />;

  // Get last 15 alerts
  const tickerItems = alerts?.slice(0, 15) || [];
  
  if (tickerItems.length === 0) {
    return <div className="flex-1 flex justify-center text-xs font-mono text-ink/40">Waiting for signals...</div>;
  }

  const getStatusDisplay = (item: PredictionLog) => {
    const isFlagged = item.status === 'PENDING_REVIEW' && item.risk_level === 'high';
    const text = isFlagged ? 'FLAGGED' : item.status;
    const colorClass = isFlagged ? 'text-rust' : item.status === 'PENDING_REVIEW' ? 'text-clay' : 'text-ink/70';
    return { text, colorClass };
  };

  return (
    <div className="flex-1 overflow-hidden mx-8 relative flex items-center h-6 group">
      {/* Masking gradients */}
      <div className="absolute left-0 top-0 bottom-0 w-12 bg-gradient-to-r from-paper to-transparent z-10 pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-paper to-transparent z-10 pointer-events-none" />
      
      <div className="flex whitespace-nowrap animate-marquee group-hover:[animation-play-state:paused]">
        {tickerItems.map((item, idx) => {
          const { text, colorClass } = getStatusDisplay(item);
          return (
            <span key={item.id + idx} className="inline-flex items-center text-xs font-mono text-ink mx-4">
              {item.transaction_id} <span className="mx-2 text-ink/30">·</span> 
              ${item.amount.toFixed(2)} <span className="mx-2 text-ink/30">·</span>
              <span className={cn("font-medium", colorClass)}>
                {text}
              </span>
            </span>
          )
        })}
        {/* Duplicate for seamless looping */}
        {tickerItems.map((item, idx) => {
          const { text, colorClass } = getStatusDisplay(item);
          return (
            <span key={`dup-${item.id}-${idx}`} className="inline-flex items-center text-xs font-mono text-ink mx-4">
              {item.transaction_id} <span className="mx-2 text-ink/30">·</span> 
              ${item.amount.toFixed(2)} <span className="mx-2 text-ink/30">·</span>
              <span className={cn("font-medium", colorClass)}>
                {text}
              </span>
            </span>
          )
        })}
      </div>
    </div>
  )
}
