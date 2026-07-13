function SearchBar({ search, setSearch }) {
  return (
    <input
      type="text"
      placeholder="Search by ID or Service..."
      value={search}
      onChange={(e) => setSearch(e.target.value)}
      className="border rounded-lg p-2 w-full"
    />
  );
}

export default SearchBar;
