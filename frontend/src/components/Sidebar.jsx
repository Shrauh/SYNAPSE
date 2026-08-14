import React from "react";
import { NavLink } from "react-router-dom";

import {
  LayoutDashboard,
  AlertTriangle,
  FileText,
  BookOpen,
  BarChart3,
  BrainCircuit,
  Settings,
  LogOut,
  ShieldCheck,
} from "lucide-react";

function Sidebar() {
  const menuItems = [
    {
      title: "Dashboard",
      icon: <LayoutDashboard size={20} />,
      path: "/",
    },
    {
      title: "Incidents",
      icon: <AlertTriangle size={20} />,
      path: "/incidents",
    },
    {
      title: "Incident Details",
      icon: <FileText size={20} />,
      path: "/incident-detail",
    },
    {
      title: "Runbooks",
      icon: <BookOpen size={20} />,
      path: "/runbooks",
    },
    {
      title: "Metrics",
      icon: <BarChart3 size={20} />,
      path: "/metrics",
    },
    {
      title: "AI Reports",
      icon: <BrainCircuit size={20} />,
      path: "/reports",
    },
    {
      title: "Settings",
      icon: <Settings size={20} />,
      path: "/settings",
    },
  ];

  return (
    <aside className="w-72 min-h-screen bg-slate-900 text-white flex flex-col justify-between shadow-xl">

      {/* Logo */}

      <div>

        <div className="flex items-center gap-3 p-6 border-b border-slate-700">

          <div className="bg-blue-600 p-3 rounded-xl">

            <ShieldCheck size={28} />

          </div>

          <div>

            <h1 className="text-2xl font-bold">

              SYNAPSE

            </h1>

            <p className="text-xs text-gray-300">

              AI Incident Platform

            </p>

          </div>

        </div>

        {/* Navigation */}

        <nav className="mt-6 px-4">

          {menuItems.map((item) => (

            <NavLink
              key={item.title}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-4 p-4 rounded-xl mb-2 transition-all duration-300 ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : "hover:bg-slate-700 text-gray-300"
                }`
              }
            >
              {item.icon}

              <span className="font-medium">

                {item.title}

              </span>

            </NavLink>

          ))}

        </nav>

      </div>

      {/* Bottom */}

      <div className="p-5 border-t border-slate-700">

        <div className="bg-slate-800 rounded-xl p-4 mb-5">

          <p className="text-sm text-gray-300">

            Project Status

          </p>

          <h3 className="font-bold text-lg text-green-400">

            Development Mode

          </h3>

        </div>

        <button className="flex items-center gap-3 w-full bg-red-600 hover:bg-red-700 p-3 rounded-xl transition">

          <LogOut size={20} />

          Logout

        </button>

      </div>

    </aside>
  );
}

export default Sidebar;
