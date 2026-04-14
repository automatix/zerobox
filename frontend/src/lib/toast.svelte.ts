export type ToastType = 'success' | 'error' | 'info';

export interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

let toasts: Toast[] = $state([]);
let nextId = 0;

export function addToast(message: string, type: ToastType = 'info', duration = 4000): void {
  const id = nextId++;
  toasts.push({ id, message, type });
  setTimeout(() => removeToast(id), duration);
}

export function removeToast(id: number): void {
  toasts = toasts.filter((t) => t.id !== id);
}

export function getToasts(): Toast[] {
  return toasts;
}
