interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <div className="w-full max-w-xl">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search courses..."
        className="w-full px-4 py-2 border border-gray-300 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50
          bg-card dark:bg-card-dark text-foreground dark:text-foreground-dark placeholder-muted-foreground dark:placeholder-muted-foreground-dark"
      />
    </div>
  );
}
