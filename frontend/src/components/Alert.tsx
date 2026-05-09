import { AlertCircle, CheckCircle, X } from 'lucide-react';
import { clsx } from 'clsx';

interface Props {
  type: 'error' | 'success' | 'info';
  message: string;
  onClose?: () => void;
}

export default function Alert({ type, message, onClose }: Props) {
  return (
    <div className={clsx(
      'flex items-start gap-3 rounded-lg p-4 text-sm',
      type === 'error' && 'bg-red-50 text-red-800 border border-red-200',
      type === 'success' && 'bg-green-50 text-green-800 border border-green-200',
      type === 'info' && 'bg-blue-50 text-blue-800 border border-blue-200',
    )}>
      {type === 'error' && <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />}
      {type === 'success' && <CheckCircle className="w-5 h-5 mt-0.5 shrink-0" />}
      <span className="flex-1">{message}</span>
      {onClose && (
        <button onClick={onClose} className="shrink-0 hover:opacity-70">
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
