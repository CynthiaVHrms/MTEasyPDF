type FileInputProps = {
  label: string;
  name: string;
  required?: boolean;
  accept?: string;
  helperText?: string;
  onChange: (file: File | null) => void;
};

export function FileInput({
  label,
  name,
  required = false,
  accept,
  helperText,
  onChange,
}: FileInputProps) {
  return (
    <label className="block rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-4 transition hover:border-blue-400 hover:bg-blue-50/40">
      <span className="mb-2 block text-sm font-semibold text-slate-700">
        {label} {required && <span className="text-red-500">*</span>}
      </span>

      <input
        name={name}
        type="file"
        required={required}
        accept={accept}
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
        className="block w-full cursor-pointer text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-blue-600 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-blue-700"
      />

      {helperText && (
        <p className="mt-2 text-xs text-slate-500">{helperText}</p>
      )}
    </label>
  );
}