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
        className="w-full px-4 py-2 border dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500
          bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
      />
    </div>
  );
}
