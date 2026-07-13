import React from "react";

function Navbar() {
  return (
    <nav className="bg-blue-900 text-white h-16 flex justify-between items-center px-6 shadow">

      <h1 className="text-2xl font-bold">
        SYNAPSE
      </h1>

      <div className="flex items-center gap-4">

        <input
          type="text"
          placeholder="Search..."
          className="rounded px-3 py-2 text-black"
        />

        <img
          src="https://ui-avatars.com/api/?name=Shrushti"
          alt="Profile"
          className="w-10 h-10 rounded-full"
        />

      </div>

    </nav>
  );
}

export default Navbar;
