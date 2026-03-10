import * as React from "react";
import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  // Base: layout, font, transitions, focus, disabled
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium " +
  "transition-[background-color,border-color,box-shadow,transform] duration-[150ms] ease-[cubic-bezier(0.2,0,0.2,1)] " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0EA5C2] focus-visible:ring-offset-2 focus-visible:shadow-[0_0_0_3px_rgba(14,165,194,0.18)] " +
  "active:scale-[0.98] active:shadow-none " +
  "disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "border border-[var(--navy-900)] bg-[var(--navy-900)] text-white " +
          "hover:border-[var(--navy-800)] hover:bg-[var(--navy-800)] hover:shadow-[0_4px_12px_rgba(15,23,42,0.18)]",
        secondary:
          "border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] " +
          "hover:bg-[#F1F5F9] hover:border-[#C8D0DA] hover:shadow-[0_2px_8px_rgba(15,23,42,0.07)]",
        ghost:
          "text-[var(--text-secondary)] " +
          "hover:bg-[#EEF2F7] hover:text-[var(--text-primary)]",
        default:
          "border border-[var(--navy-900)] bg-[var(--navy-900)] text-white " +
          "hover:border-[var(--navy-800)] hover:bg-[var(--navy-800)] hover:shadow-[0_4px_12px_rgba(15,23,42,0.18)]",
        outline:
          "border border-[var(--border)] bg-[var(--surface)] text-[var(--text-primary)] " +
          "hover:bg-[#F1F5F9] hover:border-[#C8D0DA] hover:shadow-[0_2px_8px_rgba(15,23,42,0.07)]",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        link:
          "text-[var(--navy-800)] underline-offset-4 hover:underline",
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
