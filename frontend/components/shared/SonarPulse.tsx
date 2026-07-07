"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";

interface SonarPulseProps {
  children: React.ReactNode;
  trigger: boolean;
  color?: 'ember' | 'signal';
}

export function SonarPulse({ children, trigger, color = 'ember' }: SonarPulseProps) {
  const [shouldAnimate, setShouldAnimate] = useState(false);
  const colorClass = color === 'ember' ? 'bg-ember' : 'bg-signal';

  useEffect(() => {
    // Only animate if the user hasn't requested reduced motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    
    if (trigger && !prefersReducedMotion) {
      setShouldAnimate(true);
      // Reset animation state after it finishes
      const timer = setTimeout(() => setShouldAnimate(false), 2000);
      return () => clearTimeout(timer);
    } else if (trigger && prefersReducedMotion) {
      // Reduced motion fallback: just a quick opacity flash, or do nothing.
      setShouldAnimate(true);
      const timer = setTimeout(() => setShouldAnimate(false), 500);
      return () => clearTimeout(timer);
    }
  }, [trigger]);

  const circleVariants: any = {
    initial: { scale: 0.8, opacity: 0.6 },
    animate: (custom: number) => ({
      scale: 2.2,
      opacity: 0,
      transition: {
        duration: 0.9,
        ease: "easeOut",
        delay: custom * 0.15,
      }
    }),
    reducedAnimate: {
      opacity: [0.5, 1, 0.5],
      transition: { duration: 0.5 }
    }
  };

  return (
    <div className="relative inline-flex items-center justify-center">
      <AnimatePresence>
        {shouldAnimate && (
          <>
            {/* Outer Ring */}
            <motion.div
              key="pulse-1"
              className={`absolute inset-0 rounded-full ${colorClass}`}
              variants={circleVariants}
              initial="initial"
              animate="animate"
              custom={0}
              style={{ originX: 0.5, originY: 0.5 }}
            />
            {/* Inner Ring */}
            <motion.div
              key="pulse-2"
              className={`absolute inset-0 rounded-full ${colorClass}`}
              variants={circleVariants}
              initial="initial"
              animate="animate"
              custom={1}
              style={{ originX: 0.5, originY: 0.5 }}
            />
          </>
        )}
      </AnimatePresence>
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
}
