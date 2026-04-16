import * as React from "react";

import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/label";

function Field({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("grid gap-2.5", className)} {...props} />;
}

function FieldLabel({ className, ...props }: React.ComponentProps<typeof Label>) {
  return <Label className={cn("text-sm font-semibold", className)} {...props} />;
}

function FieldHint({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-xs text-muted-foreground", className)} {...props} />;
}

export { Field, FieldHint, FieldLabel };
