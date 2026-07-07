"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { ShieldAlert, Send } from "lucide-react"

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface CopilotChatProps {
  caseId: string;
  onEscalate?: () => void;
}

export function CopilotChat({ caseId, onEscalate }: CopilotChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'I am your Analyst Copilot. I have reviewed the transaction and ML features. How can I help?' }
  ])
  const [input, setInput] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isStreaming) return

    const userMsg = input
    setInput("")
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setIsStreaming(true)

    // Mock streaming response
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])
    
    const mockResponse = "Based on the SHAP values, this transaction was flagged primarily due to an unusually high velocity of transactions from this IP address in the last 10 minutes. I highly recommend escalating this to a Senior Analyst. [RECOMMEND_ESCALATION]"
    let currentText = ""
    
    for (let i = 0; i < mockResponse.length; i++) {
      await new Promise(r => setTimeout(r, 20))
      currentText += mockResponse[i]
      setMessages(prev => {
        const newMsgs = [...prev]
        newMsgs[newMsgs.length - 1].content = currentText
        return newMsgs
      })
    }
    
    setIsStreaming(false)
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-frost border border-ink/12 rounded-sm shadow-[0_1px_3px_rgba(58,34,26,0.08)]">
      <div className="p-4 border-b border-ink/10 bg-frost-strong flex items-center gap-2">
        <ShieldAlert className="w-4 h-4 text-ink" />
        <span className="font-display text-sm font-medium text-ink">Analyst Copilot</span>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => {
          const hasEscalation = msg.role === 'assistant' && msg.content.includes('[RECOMMEND_ESCALATION]')
          const cleanContent = msg.content.replace('[RECOMMEND_ESCALATION]', '')

          return (
            <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              <div className={`max-w-[85%] rounded-md p-3 text-sm font-sans ${
                msg.role === 'user' 
                  ? 'bg-paper border border-ink/15 text-ink' 
                  : 'bg-frost-strong border border-ink/10 text-ink'
              }`}>
                {cleanContent}
              </div>
              
              {hasEscalation && onEscalate && (
                <button 
                  onClick={onEscalate}
                  className="mt-2 text-[10px] font-medium bg-rust/10 text-rust px-2 py-1 rounded-sm uppercase tracking-wide border border-rust/20 hover:bg-rust/20 transition-colors"
                >
                  Action: Escalate Case
                </button>
              )}
            </div>
          )
        })}
      </div>

      <form onSubmit={handleSubmit} className="p-3 border-t border-ink/10 bg-frost">
        <div className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about this alert..."
            className="w-full bg-paper border border-ink/20 rounded-md pl-3 pr-10 py-2 text-sm text-ink focus:outline-none focus:border-clay transition-colors"
          />
          <button 
            type="submit" 
            disabled={!input.trim() || isStreaming}
            className="absolute right-2 p-1 text-ink/60 hover:text-clay disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  )
}
