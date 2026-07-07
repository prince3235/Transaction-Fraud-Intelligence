"use client"

import { StatCard } from "@/components/shared/StatCard"
import { DataTable } from "@/components/shared/DataTable"
import { RiskBadge } from "@/components/shared/RiskBadge"
import { OpaquePanel } from "@/components/shared/OpaquePanel"
import { useRole } from "@/store"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api/client"
import { useRouter } from "next/navigation"
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

const chartData = [
  { time: "00:00", volume: 1200, fraudRate: 0.1 },
  { time: "04:00", volume: 900, fraudRate: 0.2 },
  { time: "08:00", volume: 2400, fraudRate: 0.5 },
  { time: "12:00", volume: 3800, fraudRate: 1.2 },
  { time: "16:00", volume: 4200, fraudRate: 1.8 },
  { time: "20:00", volume: 2100, fraudRate: 0.8 },
  { time: "24:00", volume: 1500, fraudRate: 0.3 },
]

export default function CommandCenterPage() {
  const role = useRole()
  const router = useRouter()
  
  const { data: alerts, isLoading } = useQuery({
    queryKey: ['alerts', 'high'],
    queryFn: () => api.getAlerts(1, 'PENDING_REVIEW'),
    select: (data) => data.filter(a => a.risk_level === 'high').slice(0, 5),
    initialData: []
  })

  const isJunior = role === "Junior Analyst"

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Transactions (24h)" value="14,203" trend={5.2} />
        <StatCard label="High-Risk Flags" value="42" trend={12} tone="danger" />
        <StatCard label="Open Cases" value="18" trend={-2.1} />
        
        {!isJunior && (
          <StatCard label="Avg Latency" value="24ms" trend={-0.5} />
        )}
        {isJunior && (
          <StatCard label="Cases Resolved" value="7" trend={15} />
        )}
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Recent High-Risk Alerts */}
        <div className="lg:col-span-1 space-y-4">
          <h2 className="font-display text-lg font-medium text-mist">Recent High-Risk Alerts</h2>
          <DataTable 
            data={alerts || []}
            isLoading={isLoading}
            onRowClick={(item) => router.push(`/cases/case-${item.id}`)}
            columns={[
              { 
                header: "Txn ID", 
                accessorKey: "transaction_id",
                className: "font-mono text-xs text-mist/80"
              },
              { 
                header: "Amount",
                cell: (item) => <span className="font-mono text-xs">${item.amount.toFixed(2)}</span>
              },
              {
                header: "Risk",
                cell: (item) => <RiskBadge level={item.risk_level} />
              }
            ]}
          />
        </div>

        {/* Right Column: Trend Chart */}
        <div className="lg:col-span-2 space-y-4 flex flex-col">
          <h2 className="font-display text-lg font-medium text-mist">Volume & Fraud Rate</h2>
          <OpaquePanel className="flex-1 p-6 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--signal)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--signal)" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorFraud" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--ember)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--ember)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" stroke="var(--mist)" opacity={0.3} fontSize={12} tickLine={false} axisLine={false} />
                <YAxis yAxisId="left" stroke="var(--mist)" opacity={0.3} fontSize={12} tickLine={false} axisLine={false} />
                <YAxis yAxisId="right" orientation="right" stroke="var(--ember)" opacity={0.3} fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--trench)', borderColor: 'rgba(175,221,229,0.1)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--mist)', fontFamily: 'var(--font-inter)' }}
                  labelStyle={{ color: 'rgba(175,221,229,0.7)', fontFamily: 'var(--font-mono)' }}
                />
                <Area yAxisId="left" type="monotone" dataKey="volume" stroke="var(--signal)" fillOpacity={1} fill="url(#colorVolume)" />
                <Area yAxisId="right" type="monotone" dataKey="fraudRate" stroke="var(--ember)" fillOpacity={1} fill="url(#colorFraud)" />
              </AreaChart>
            </ResponsiveContainer>
          </OpaquePanel>
        </div>

      </div>
    </div>
  )
}
