import { useState } from "react";

import incidents from "../data/incidents";

import SearchBar from "../components/SearchBar";

import FilterBar from "../components/FilterBar";

import IncidentCard from "../components/IncidentCard";

function IncidentList() {

const [search, setSearch] = useState("");

const [severity, setSeverity] = useState("");

const [status, setStatus] = useState("");

const filtered = incidents.filter((item) => {

const matchSearch =
item.service.toLowerCase().includes(search.toLowerCase()) ||
item.id.toLowerCase().includes(search.toLowerCase());

const matchSeverity =
severity === "" || item.severity === severity;

const matchStatus =
status === "" || item.status === status;

return matchSearch && matchSeverity && matchStatus;

});

return (

<div className="p-8">

<h1 className="text-3xl font-bold mb-6">

Incident List

</h1>

<div className="flex gap-4 mb-6">

<SearchBar

search={search}

setSearch={setSearch}

/>

<FilterBar

severity={severity}

setSeverity={setSeverity}

status={status}

setStatus={setStatus}

/>

</div>

<div className="grid grid-cols-1 md:grid-cols-2 gap-5">

{

filtered.map((incident)=>(

<IncidentCard

key={incident.id}

incident={incident}

/>

))

}

</div>

</div>

);

}

export default IncidentList;
