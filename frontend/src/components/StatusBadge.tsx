import { Badge } from "./ui";
import type { OrderStatus } from "@/lib/types";

const STATUS: Record<OrderStatus, { label: string; tone: "slate" | "brand" | "sky" | "emerald" | "rose" }> = {
  draft: { label: "Qoralama", tone: "slate" },
  confirmed: { label: "Tasdiqlangan", tone: "brand" },
  shipped: { label: "Jo'natilgan", tone: "sky" },
  delivered: { label: "Yetkazilgan", tone: "emerald" },
  cancelled: { label: "Bekor qilingan", tone: "rose" },
};

export const ORDER_STATUSES = Object.entries(STATUS).map(([value, { label }]) => ({
  value: value as OrderStatus,
  label,
}));

export function StatusBadge({ status }: { status: OrderStatus }) {
  const { label, tone } = STATUS[status];
  return (
    <Badge tone={tone}>
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {label}
    </Badge>
  );
}
