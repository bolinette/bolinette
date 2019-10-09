export default class ToastData {
  public id: number;
  public message: string;
  public type: 'info' | 'success' | 'warning' | 'error';
  public duration: number;

  constructor(id: number, params: ToastOptions) {
    this.id = id;
    this.message = params.message;
    this.type = params.type;
    this.duration = params.duration || 5000;
  }
}

export interface ToastOptions {
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  duration?: number;
}
