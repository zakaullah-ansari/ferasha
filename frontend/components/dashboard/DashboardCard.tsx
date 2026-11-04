import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/cn";

interface DashboardCardProps extends Omit<React.ComponentProps<typeof Card>, "title"> {
  readonly title: string;
  readonly description?: string;
  /** Top right: a badge or a link. */
  readonly action?: React.ReactNode;
}

/**
 * Every dashboard panel. The title is set at a size where the display face
 * stays legible; at the card's default small size it reads faint.
 */
export function DashboardCard({ title, description, action, children, className, ...props }: DashboardCardProps) {
  return (
    // min-w-0: as a grid item a card must be able to shrink, or a wide table pushes the page sideways on phones.
    <Card className={cn("min-w-0", className)} {...props}>
      <CardHeader>
        <CardTitle className="text-xl">{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
        {action && <CardAction>{action}</CardAction>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}
