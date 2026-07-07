"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { GlassPanel } from "@/components/shared/GlassPanel"
import { Button } from "@/components/ui/button"
import { Shield } from "lucide-react"
import { useStore } from "@/store"

export default function LoginPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState<string>("Senior Analyst")
  const setUser = useStore(state => state.setUser)
  const router = useRouter()

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    // Mock login setting user session
    setUser({
      id: "u-123",
      name: "Alex Analyst",
      email: "alex@fraudplatform.internal",
      role: role as any,
    })
    router.push("/command-center")
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-abyss">
      {/* Subtle static radial gradient */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(15,164,175,0.1)_0%,transparent_50%)] pointer-events-none" />

      <GlassPanel className="w-full max-w-md p-8 relative z-10 flex flex-col gap-6">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="w-12 h-12 rounded-full bg-signal/20 flex items-center justify-center">
            <Shield className="w-6 h-6 text-signal" />
          </div>
          <div>
            <h1 className="font-display text-2xl font-medium text-mist mb-1">The Abyss</h1>
            <p className="text-sm font-sans text-mist/60">Fraud Intelligence Platform</p>
          </div>
        </div>

        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-sans text-mist/70 uppercase tracking-wide">Username</label>
            <input 
              type="text" 
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="bg-abyss/50 border border-mist/20 rounded-md px-3 py-2 text-mist focus:outline-none focus:border-signal transition-colors font-mono text-sm"
              placeholder="analyst.a"
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-sans text-mist/70 uppercase tracking-wide">Password</label>
            <input 
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)} 
              className="bg-abyss/50 border border-mist/20 rounded-md px-3 py-2 text-mist focus:outline-none focus:border-signal transition-colors font-mono text-sm"
              placeholder="••••••••"
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-sans text-mist/70 uppercase tracking-wide">Mock Role</label>
            <select
              value={role}
              onChange={e => setRole(e.target.value)}
              className="bg-abyss/50 border border-mist/20 rounded-md px-3 py-2 text-mist focus:outline-none focus:border-signal transition-colors font-sans text-sm"
            >
              <option value="Junior Analyst">Junior Analyst</option>
              <option value="Senior Analyst">Senior Analyst</option>
              <option value="Data Scientist">Data Scientist</option>
              <option value="Admin/Executive">Admin/Executive</option>
            </select>
          </div>
          <Button type="submit" className="w-full mt-2 font-display uppercase tracking-wide bg-signal text-[var(--text-on-signal)] hover:bg-signal/80">
            Enter Command Center
          </Button>
        </form>
      </GlassPanel>
    </div>
  )
}
