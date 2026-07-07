"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { BookOpen, Activity, Bell, FileText, Database, ShieldAlert, FileBarChart, PlayCircle, LogOut } from "lucide-react"
import { cn } from "@/lib/utils"
import { useStore, useRole } from "@/store"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

const NAV_ITEMS = [
  { name: "Command Center", href: "/command-center", icon: Activity, roles: ["Junior Analyst", "Senior Analyst", "Data Scientist", "Admin/Executive"] },
  { name: "Live Alerts", href: "/alerts", icon: Bell, roles: ["Junior Analyst", "Senior Analyst", "Data Scientist", "Admin/Executive"] },
  { name: "Cases", href: "/cases", icon: FileText, roles: ["Junior Analyst", "Senior Analyst", "Data Scientist", "Admin/Executive"] },
  { name: "Model Registry", href: "/model-registry", icon: Database, roles: ["Data Scientist", "Admin/Executive"] },
  { name: "Business Rules", href: "/business-rules", icon: ShieldAlert, roles: ["Admin/Executive"] },
  { name: "Audit Log", href: "/audit-log", icon: FileBarChart, roles: ["Admin/Executive"] },
  { name: "Simulation", href: "/simulation", icon: PlayCircle, roles: ["Junior Analyst", "Senior Analyst", "Data Scientist", "Admin/Executive"] },
]

export function Sidebar() {
  const pathname = usePathname()
  const role = useRole()
  const user = useStore((state) => state.user)
  const setUser = useStore((state) => state.setUser)

  return (
    <aside className="w-[240px] flex-shrink-0 flex flex-col h-screen rounded-none bg-ink text-paper border-r border-ink/10">
      <div className="p-6 flex items-center gap-3">
        <BookOpen className="w-6 h-6 text-paper" />
        <span className="font-display font-medium text-lg text-paper tracking-tight">The Ledger</span>
      </div>

      <nav className="flex-1 px-4 space-y-1 mt-4 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          if (role && !item.roles.includes(role)) return null;

          const isActive = pathname.startsWith(item.href)
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg font-sans text-sm transition-all duration-150",
                isActive 
                  ? "bg-clay text-paper font-medium" 
                  : "text-paper/60 hover:text-paper hover:bg-clay/20"
              )}
            >
              <item.icon className="w-4 h-4" />
              {item.name}
            </Link>
          )
        })}
      </nav>

      {user && (
        <div className="p-4 mt-auto border-t border-paper/10">
          <div className="flex items-center gap-3">
            <Avatar className="h-9 w-9 bg-clay text-paper">
              <AvatarImage src={user.avatar_url} />
              <AvatarFallback className="bg-clay text-paper">{user.name.charAt(0)}</AvatarFallback>
            </Avatar>
            <div className="flex flex-col flex-1 min-w-0">
              <span className="text-sm font-medium text-paper truncate">{user.name}</span>
              <span className="text-[10px] text-paper/60 truncate">{user.role}</span>
            </div>
            <button 
              onClick={() => setUser(null)}
              className="p-1.5 text-paper/60 hover:text-paper hover:bg-clay/20 rounded-md transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </aside>
  )
}
