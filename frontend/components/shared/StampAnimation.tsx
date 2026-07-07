"use client"

import { motion, useReducedMotion } from "framer-motion"
import { ReactNode, useEffect, useState } from "react"
import { cn } from "@/lib/utils"

interface StampAnimationProps {
  children: ReactNode;
  trigger?: boolean;
  tone?: 'default' | 'danger';
  className?: string;
}

export function StampAnimation({ children, trigger = true, tone = 'default', className }: StampAnimationProps) {
  const shouldReduceMotion = useReducedMotion();
  const [hasFired, setHasFired] = useState(false);

  useEffect(() => {
    if (trigger && !hasFired) {
      setHasFired(true);
    }
  }, [trigger, hasFired]);

  const variants = {
    initial: shouldReduceMotion ? { opacity: 0 } : { opacity: 0, scale: 1.4, rotate: -8 },
    animate: shouldReduceMotion ? { opacity: 1 } : { opacity: 1, scale: 1, rotate: -3 }
  };

  const isDanger = tone === 'danger';

  return (
    <motion.div
      variants={variants}
      initial={trigger && !hasFired ? "initial" : "animate"}
      animate="animate"
      transition={{
        type: shouldReduceMotion ? "tween" : "spring",
        stiffness: 400,
        damping: 15,
        duration: shouldReduceMotion ? 0.3 : undefined
      }}
      className={cn(
        "inline-flex items-center justify-center font-display border-2 px-2 py-0.5 rounded-sm uppercase tracking-widest font-bold",
        isDanger ? "text-rust border-rust" : "text-ink border-ink",
        className
      )}
      style={{
        transformOrigin: "center center"
      }}
    >
      {children}
    </motion.div>
  );
}
