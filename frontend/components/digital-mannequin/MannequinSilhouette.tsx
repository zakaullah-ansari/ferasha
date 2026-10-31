import React from 'react';
import { cn } from '@/lib/utils';

interface MannequinSilhouetteProps {
  className?: string;
  highlightAreas?: string[];
  modestyLevel?: 'full' | 'partial' | 'none';
}

export const MannequinSilhouette: React.FC<MannequinSilhouetteProps> = ({
  className,
  highlightAreas = [],
  modestyLevel = 'full'
}) => {
  // This SVG represents a high-fashion editorial silhouette.
  // We use a simplified, elegant vector that serves as a canvas for the fit/modesty overlay.
  return (
    <svg
      viewBox="0 0 200 500"
      className={cn("w-full h-full fill-ink-200 transition-all duration-700", className)}
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Main Body Silhouette */}
      <path
        d="M100,20 C110,20 120,30 120,50 C120,70 110,80 100,80 C90,80 80,70 80,50 C80,30 90,20 100,20 Z
           M80,85 L120,85 L130,150 L120,250 L100,260 L80,250 L70,150 Z
           M70,160 L130,160 L140,300 L120,480 L80,480 L60,300 Z"
        fill="currentColor"
      />

      {/* Modesty Overlays: These are conditionally rendered based on the product's modesty profile */}
      {modestyLevel === 'full' && (
        <path
          d="M80,85 L120,85 L125,120 L75,120 Z"
          className="fill-primary/30 transition-all duration-500"
        />
      )}

      {/* Highlight Areas: used for showing specific measurement points or tailoring zones */}
      {highlightAreas.map((area, idx) => (
        <circle
          key={idx}
          cx={area === 'bust' ? 100 : area === 'waist' ? 100 : 100}
          cy={area === 'bust' ? 150 : area === 'waist' ? 200 : 300}
          r="4"
          className="fill-gold-500 animate-pulse"
        />
      ))}
    </svg>
  );
};
