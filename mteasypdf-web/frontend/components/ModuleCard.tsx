type ModuleCardProps = {
  icon: string;
  title: string;
  description: string;
  active: boolean;
  onClick: () => void;
};

export function ModuleCard({
  icon,
  title,
  description,
  active,
  onClick,
}: ModuleCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-2xl border p-4 text-left transition ${
        active
          ? "border-blue-500 bg-blue-50 shadow-sm"
          : "border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50"
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`flex h-11 w-11 items-center justify-center rounded-xl text-xl ${
            active ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-700"
          }`}
        >
          {icon}
        </div>

        <div>
          <p className="font-bold text-slate-900">{title}</p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            {description}
          </p>
        </div>
      </div>
    </button>
  );
}