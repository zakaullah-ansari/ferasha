import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import { type MeasurementPoint, MannequinSilhouette } from "./MannequinSilhouette";

interface DigitalMannequinProps {
  /** The measurement the customer is currently entering, if any. */
  readonly activeMeasurement?: MeasurementPoint;
  readonly coveredNeckline?: boolean;
}

/** Visual fit guide: shows where the active measurement is taken. */
export function DigitalMannequin({ activeMeasurement, coveredNeckline }: DigitalMannequinProps) {
  return (
    <Card className="mx-auto w-full max-w-xs">
      <CardHeader>
        <CardTitle className="text-sm font-medium uppercase tracking-widest text-muted-foreground">
          Fit guide
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4">
        <div className="aspect-[2/5] w-full">
          <MannequinSilhouette highlight={activeMeasurement} coveredNeckline={coveredNeckline} />
        </div>
        {/* Live region so the highlighted point is announced, not only drawn. */}
        <p aria-live="polite" className="min-h-6">
          {activeMeasurement && (
            <Badge variant="secondary" className="capitalize">
              Measuring: {activeMeasurement}
            </Badge>
          )}
        </p>
      </CardContent>
    </Card>
  );
}
