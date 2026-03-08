import { Navigate } from "react-router-dom";

const DashboardSecurity = () => {
  return <Navigate to="/dashboard/account?tab=security" replace />;
};

export default DashboardSecurity;
