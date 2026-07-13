function FilterBar({
  severity,
  setSeverity,
  status,
  setStatus
}) {
  return (
    <div className="flex gap-4">

      <select
        value={severity}
        onChange={(e)=>setSeverity(e.target.value)}
        className="border rounded-lg p-2"
      >
        <option value="">All Severity</option>
        <option>Critical</option>
        <option>High</option>
        <option>Medium</option>
        <option>Low</option>
      </select>

      <select
        value={status}
        onChange={(e)=>setStatus(e.target.value)}
        className="border rounded-lg p-2"
      >
        <option value="">All Status</option>
        <option>Open</option>
        <option>Resolved</option>
        <option>Closed</option>
      </select>

    </div>
  );
}

export default FilterBar;
