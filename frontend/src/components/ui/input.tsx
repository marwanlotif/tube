import { forwardRef } from "react";

import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-lg border border-edge bg-surface px-3 text-sm text-ink placeholder:text-faint",
        "transition-colors hover:border-[#333b46] focus:border-accent/60 focus:outline-none focus:ring-2 focus:ring-accent/15",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export const Select = forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "h-10 w-full appearance-none rounded-lg border border-edge bg-surface px-3 pr-8 text-sm text-ink",
      "bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%2212%22 height=%2212%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%238b939f%22 stroke-width=%222%22%3E%3Cpath d=%22m6 9 6 6 6-6%22/%3E%3C/svg%3E')] bg-[right_0.7rem_center] bg-no-repeat",
      "transition-colors hover:border-[#333b46] focus:border-accent/60 focus:outline-none focus:ring-2 focus:ring-accent/15",
      className,
    )}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = "Select";
