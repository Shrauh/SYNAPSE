import { NavLink } from "react-router-dom";

function Sidebar() {
  return (
    <aside className="w-64 bg-slate-200 p-4 min-h-screen">
      <nav className="flex flex-col gap-3">
        <NavLink to="/">Dashboard</NavLink>
        <NavLink to="/incidents">Incidents</NavLink>
        <NavLink to="/runbooks">Runbooks</NavLink>
      </nav>
    </aside>
  );
}

export default Sidebar;