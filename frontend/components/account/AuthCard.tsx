import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

/** The frame every sign-in, reset and verification screen shares. */
export function AuthCard({
  title,
  description,
  notice,
  footer,
  children,
}: {
  title: string;
  description: string;
  /** A fixed message from the app (never text taken from the URL). */
  notice?: string;
  footer?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle className="font-display text-2xl">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
        {notice && (
          <p role="status" className="mt-2 rounded-xl bg-primary/10 px-3 py-2 text-sm text-primary">
            {notice}
          </p>
        )}
      </CardHeader>
      <CardContent>{children}</CardContent>
      {footer && <CardFooter className="text-sm text-muted-foreground">{footer}</CardFooter>}
    </Card>
  );
}
