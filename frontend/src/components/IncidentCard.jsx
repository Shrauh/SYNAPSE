function IncidentCard({ incident }) {

  const severityColor = {
    Critical: "bg-red-600",
    High: "bg-orange-500",
    Medium: "bg-yellow-500",
    Low: "bg-green-500"
  };

  return (

<div className="border rounded-xl shadow-md p-5">

<h2 className="font-bold text-lg">
{incident.id}
</h2>

<p>
Service:
<strong> {incident.service}</strong>
</p>

<p>

Severity:

<span
className={`text-white px-2 py-1 rounded ml-2 ${severityColor[incident.severity]}`}
>

{incident.severity}

</span>

</p>

<p>Status: {incident.status}</p>

<p>{incident.timestamp}</p>

</div>

  );

}

export default IncidentCard;
