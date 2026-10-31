import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { MannequinSilhouette } from './MannequinSilhouette';
import { cn } from '@/lib/utils';
import { Label } from '@/components/ui/label';

interface DigitalMannequinProps {
  productModesty: 'full' | 'partial' | 'none';
  activeMeasurement?: string;
  onAreaClick?: (area: string) => void;
}

export const DigitalMannequin: React.FC<DigitalMannequinProps> = ({
  productModesty,
  activeMeasurement,
  onAreaClick
}) => {
  const [hoveredArea, setHoveredArea] = useState<string | null>(null);

  return (
    <div className="relative w-full aspect-[1/2.5] max-w-xs mx-auto bg-ink-50 rounded-3xl p-8 border border-ink-100 shadow-inner">
      <div className="absolute top-6 left-0 right-0 text-center">
        <Label className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
          Visual Fit Guide
        </Label>
      </div>

      <div className="relative w-full h-full flex items-center justify-center mt-8">
        <MannequinSilhouette
          modestyLevel={productModesty}
          highlightAreas={activeMeasurement ? [activeMeasurement] : []}
          className={cn(
            "drop-shadow-2xl",
            activeMeasurement ? "fill-ink-400" : "fill-ink-200"
          )}
        />
      </div>

      {/* Tooltip for active area */}
      <AnimatePresence>
        {activeMeasurement && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute bottom-12 left-1/2 -translate-x-1/2 glass-regular px-4 py-2 rounded-full border border-white/40 shadow-lg"
          >
            <p className="text-[10px] font-medium text-ink-900 uppercase tracking-widest">
              {activeMeasurement}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
