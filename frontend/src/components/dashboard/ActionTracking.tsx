import { DashboardCard } from "@/components/ui/card";
import GovernanceEmptyState from "@/components/governance/GovernanceEmptyState";
import { ClipboardList } from "lucide-react";

export type ActionTrackingItem = {
  id: string;
  title: string;
  owner: string;
  dueDate: string;
  status: "Planned" | "In Progress" | "Completed" | "Overdue" | string;
};

type ActionTrackingProps = {
  actions: ActionTrackingItem[];
};

const statusClass = (status: string) => {
  const normalized = status.trim().toLowerCase();
  if (normalized === "overdue") return "bg-red-100 text-red-700";
  if (normalized === "completed") return "bg-green-100 text-green-700";
  if (normalized === "in progress") return "bg-blue-100 text-blue-700";
  return "bg-gray-100 text-gray-700";
};

const ActionTracking = ({ actions }: ActionTrackingProps) => {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      {actions.length === 0 ? (
        <DashboardCard title="Action Tracking" subtitle="Assigned partner actions" subtitleClassName="section-subtitle">
          <GovernanceEmptyState
            size="sm"
            icon={<ClipboardList size={18} />}
            title="No governance actions yet"
            description="Actions are created after reviewing client issues. Confirm ownership, assign due dates, and they will appear here."
            primaryAction={{ label: "Review client issues", href: "/dashboard/signals" }}
          />
        </DashboardCard>
      ) : (
        actions.map((action) => (
          <DashboardCard key={action.id} title={action.title} subtitle={`Owner: ${action.owner}`} subtitleClassName="body-text">
            <div className="space-y-2">
              <p className="body-text">Due: {action.dueDate}</p>
              <div>
                <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${statusClass(action.status)}`}>
                  {action.status}
                </span>
              </div>
            </div>
          </DashboardCard>
        ))
      )}
    </div>
  );
};

export default ActionTracking;
