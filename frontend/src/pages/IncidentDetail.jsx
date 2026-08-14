import { useState } from "react";
   import { useParams } from "react-router-dom";

   const tabs = ["Overview", "Causal Graph", "Report"];

   export default function IncidentDetail() {
     const { id } = useParams();
     const [activeTab, setActiveTab] = useState("Overview");

     return (
       <div className="p-6">
         <h1 className="text-xl font-bold mb-4">Incident #{id}</h1>
         <div className="flex gap-4 border-b mb-4">
           {tabs.map((tab) => (
             <button
               key={tab}
               onClick={() => setActiveTab(tab)}
               className={`pb-2 ${activeTab === tab ? "border-b-2 border-blue-600 font-semibold" : "text-gray-500"}`}
             >
               {tab}
             </button>
           ))}
         </div>
         {activeTab === "Overview" && <div>Mock overview content here</div>}
         {activeTab === "Causal Graph" && <div>Coming Day 4 (react-flow)</div>}
         {activeTab === "Report" && <div>Coming Day 5</div>}
       </div>
     );
   }
