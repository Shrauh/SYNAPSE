import { useState } from "react";
   import { mockIncidents } from "../data/mockIncidents";
   import SeverityBadge from "../components/SeverityBadge";

   export default function IncidentList() {
     const [search, setSearch] = useState("");
     const [severityFilter, setSeverityFilter] = useState("all");
     const [statusFilter, setStatusFilter] = useState("all");

     const filtered = mockIncidents.filter((incident) => {
       const matchesSearch = incident.service.toLowerCase().includes(search.toLowerCase());
       const matchesSeverity = severityFilter === "all" || incident.severity === severityFilter;
       const matchesStatus = statusFilter === "all" || incident.status === statusFilter;
       return matchesSearch && matchesSeverity && matchesStatus;
     });

     return (
       <div className="p-6">
         <h1 className="text-2xl font-bold mb-4">Incidents</h1>

         <div className="flex gap-3 mb-4">
           <input
             type="text"
             placeholder="Search by service..."
             value={search}
             onChange={(e) => setSearch(e.target.value)}
             className="border rounded px-3 py-2 flex-1"
           />
           <select
             value={severityFilter}
             onChange={(e) => setSeverityFilter(e.target.value)}
             className="border rounded px-3 py-2"
           >
             <option value="all">All Severities</option>
             <option value="critical">Critical</option>
             <option value="high">High</option>
             <option value="medium">Medium</option>
             <option value="low">Low</option>
           </select>
           <select
             value={statusFilter}
             onChange={(e) => setStatusFilter(e.target.value)}
             className="border rounded px-3 py-2"
           >
             <option value="all">All Statuses</option>
             <option value="open">Open</option>
             <option value="investigating">Investigating</option>
             <option value="resolved">Resolved</option>
           </select>
         </div>

         <div className="bg-white shadow rounded-lg divide-y">
           {filtered.map((incident) => (
             <div key={incident.id} className="flex items-center justify-between p-4 hover:bg-gray-50">
               <div>
                 <p className="font-medium">{incident.service}</p>
                 <p className="text-sm text-gray-500">{new Date(incident.timestamp).toLocaleString()}</p>
               </div>
               <div className="flex items-center gap-3">
                 <span className="text-sm capitalize text-gray-600">{incident.status}</span>
                 <SeverityBadge severity={incident.severity} />
               </div>
             </div>
           ))}
           {filtered.length === 0 && (
             <p className="p-4 text-gray-400 text-sm">No incidents match your filters.</p>
           )}
         </div>
       </div>
     );
   }
