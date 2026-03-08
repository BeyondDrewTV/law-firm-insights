import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200 ease-out hover:shadow-[0_6px_14px_rgba(15,23,42,0.12)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--navy-800)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 disabled:hover:shadow-none",
  {
    variants: {
      variant: {
        primary: "border border-[var(--navy-900)] bg-[var(--navy-900)] text-white hover:border-[var(--navy-800)] hover:bg-[var(--navy-800)]",
        secondary: "border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[#F8FAFC]",
        ghost: "text-[var(--text-secondary)] hover:bg-[#EEF2F7] hover:text-[var(--text-primary)]",

        default: "border border-[var(--navy-900)] bg-[var(--navy-900)] text-white hover:border-[var(--navy-800)] hover:bg-[var(--navy-800)]",
        outline: "border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] hover:bg-[#F8FAFC]",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        link: "text-[var(--navy-800)] underline-offset-4 hover:underline",
      },
      size: {
        default: "px-4 py-2",
        sm: "px-3 py-1.5 text-xs",
        lg: "px-5 py-2.5",
        icon: "h-9 w-9 p-0",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  },
);

Button.displayName = "Button";

export { Button, buttonVariants };
