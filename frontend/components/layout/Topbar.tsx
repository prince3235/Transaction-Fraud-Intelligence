"use client"

import { usePathname } from "next/navigation"
import { GlassPanel } from "@/components/shared/GlassPanel"
import { LiveTicker } from "./LiveTicker"
import { Bell, Wifi, WifiOff, Loader2 } from "lucide-react"
import { useStore } from "@/store"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/client"
import { cn } from "@/lib/utils"

export function Topbar() {
  const pathname = usePathname()
  const wsStatus = useStore((state) => state.wsStatus)
  
  // Format page title from pathname
  const pageTitle = pathname === "/" ? "Command Center" : 
    pathname.split('/')[1].split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')

  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.getAlerts(1),
    refetchInterval: 15000,
    initialData: []
  })

  // Count pending high-risk alerts
  const pendingHighRiskCount = alerts?.filter(a => a.status === 'PENDING_REVIEW' && a.risk_level === 'high').length || 0

  return (
    <GlassPanel as="header" className="h-16 flex-shrink-0 flex items-center justify-between px-6 rounded-none border-t-0 border-r-0 border-l-0 sticky top-0 z-40">
      <div className="flex items-center min-w-[200px]">
        <h1 className="font-display text-[18px] font-medium text-mist">{pageTitle}</h1>
      </div>

      <LiveTicker />

      <div className="flex items-center gap-4 min-w-[200px] justify-end">
        
        {/* WS Status Indicator */}
        <div className="flex items-center gap-2 px-2 py-1 rounded-md bg-trench" title={`WebSocket Status: ${wsStatus}`}>
          {wsStatus === 'connected' && <Wifi className="w-3.5 h-3.5 text-signal" />}
          {wsStatus === 'reconnecting' && <Loader2 className="w-3.5 h-3.5 text-mist/70 animate-spin" />}
          {wsStatus === 'disconnected' && <WifiOff className="w-3.5 h-3.5 text-mist/50" />}
          <span className="text-[10px] font-medium text-mist/70 uppercase tracking-wider">{wsStatus}</span>
        </div>

        {/* Notifications */}
        <div className="relative p-2">
          <Bell className="w-5 h-5 text-mist" />
          {pendingHighRiskCount > 0 && (
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-ember ring-2 ring-abyss" />
          )}
        </div>
      </div>
    </GlassPanel>
  )
}
