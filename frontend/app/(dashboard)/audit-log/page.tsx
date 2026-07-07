"use client"

import { DataTable } from "@/components/shared/DataTable"
import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { useRole } from "@/store"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight } from "lucide-react"

// Mock fetch
const fetchAuditLogs = async (page: number) => {
  // In reality: await fetch(`/api/audit-log?page=${page}`)
  await new Promise(r => setTimeout(r, 400))
  return {
    items: [
      { id: `log-${page}-1`, user_id: "Alex Analyst", action: "CASE_STATUS_UPDATE", resource_id: "case-102", timestamp: new Date().toISOString() },
      { id: `log-${page}-2`, user_id: "System", action: "RULE_TRIGGERED", resource_id: "rule-1", timestamp: new Date(Date.now() - 3600000).toISOString() },
      { id: `log-${page}-3`, user_id: "Admin Exec", action: "RULE_CREATED", resource_id: "rule-2", timestamp: new Date(Date.now() - 7200000).toISOString() },
    ],
    total: 100,
    page,
    pages: 34
  }
}

export default function AuditLogPage() {
  const role = useRole()
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['audit-logs', page],
    queryFn: () => fetchAuditLogs(page),
  })

  if (role !== "Admin/Executive") {
    return <div className="p-12 text-center text-ember font-medium">Access Denied: Admin/Executive role required.</div>
  }

  return (
    <div className="space-y-4 flex flex-col h-[calc(100vh-8rem)]">
      <div className="flex items-center justify-between flex-shrink-0">
        <h2 className="font-display text-xl font-medium text-mist">Audit Log</h2>
        <div className="flex gap-2">
          {/* Mock filters */}
          <input type="text" placeholder="Search User/Action..." className="bg-trench border border-mist/20 rounded px-3 py-1.5 text-sm text-mist outline-none focus:border-signal" />
          <input type="date" className="bg-trench border border-mist/20 rounded px-3 py-1.5 text-sm text-mist outline-none focus:border-signal" />
        </div>
      </div>

      <DataTable 
        className="flex-1"
        data={data?.items || []}
        isLoading={isLoading}
        columns={[
          { header: "Timestamp", cell: (item) => <span className="font-mono text-xs text-mist/60">{new Date(item.timestamp).toLocaleString()}</span> },
          { header: "User", accessorKey: "user_id", className: "font-medium text-sm" },
          { header: "Action", cell: (item) => <span className="text-xs bg-mist/5 px-2 py-1 rounded font-mono">{item.action}</span> },
          { header: "Resource", cell: (item) => <span className="font-mono text-xs text-signal">{item.resource_id}</span> },
        ]}
      />

      <div className="flex items-center justify-between flex-shrink-0 bg-trench p-3 border border-mist/20 rounded-xl">
        <span className="text-xs text-mist/50">Page {data?.page || 1} of {data?.pages || 1}</span>
        <div className="flex gap-2">
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1 || isLoading}
            className="border-mist/20 text-mist hover:bg-mist/10 h-7"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => setPage(p => p + 1)}
            disabled={page === (data?.pages || 1) || isLoading}
            className="border-mist/20 text-mist hover:bg-mist/10 h-7"
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
