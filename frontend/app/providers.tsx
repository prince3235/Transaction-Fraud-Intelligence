"use client"

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { useAlertsSocket } from '@/lib/ws/useAlertsSocket'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
      },
    },
  }))

  return (
    <QueryClientProvider client={queryClient}>
      <SocketManager />
      {children}
    </QueryClientProvider>
  )
}

function SocketManager() {
  useAlertsSocket()
  return null
}
