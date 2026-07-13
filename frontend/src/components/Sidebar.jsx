import React from "react";
import { NavLink } from "react-router-dom";

function Sidebar() {

  const linkStyle = ({ isActive }) =>
    isActive
      ? "block p-3 rounded bg-blue-700 text-white"
      : "block p-3 rounded hover:bg-gray-200";

  return (

    <div className="w-64 bg-gray-100 min-h-screen p-5 shadow">

      <h2 className="font-bold text-xl mb-6">
        MENU
      </h2>

      <nav className="space-y-2">

        <NavLink to="/" className={linkStyle}>
          Dashboard
        </NavLink>

        <NavLink to="/incidents" className={linkStyle}>
          Incidents
        </NavLink>

        <NavLink to="/incident-detail" className={linkStyle}>
          Incident Detail
        </NavLink>

        <NavLink to="/runbooks" className={linkStyle}>
          Runbooks
        </NavLink>

      </nav>

    </div>

  );
}

export default Sidebar;
