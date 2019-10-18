import ToastData, { ToastOptions } from '@/data/ToastData';
import { toastModule } from '@/store';
import _ from 'lodash';
import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';


@Module({name: 'toast'})
export default class UserStore extends VuexModule {
  private _toasts: ToastData[] = [];
  private _id: number = 0;
  public get id(): number {
    return this._id;
  }

  public get toasts(): ToastData[] {
    return this._toasts;
  }

  @Mutation
  public setId(value: number) {
    this._id = value;
  }

  @Mutation
  public pushToast(toast: ToastData) {
    this._toasts.push(toast);
  }

  @Mutation
  public removeToast(toast: ToastData) {
    this._toasts = _.filter(this._toasts, (t) => t.id !== toast.id);
  }

  @Action
  public addToast(params: ToastOptions) {
    const toast = new ToastData(toastModule.id, params);
    toastModule.pushToast(toast);
    toastModule.setId(toastModule.id + 1);
    setTimeout(() => {
      toastModule.removeToast(toast);
    }, toast.duration);
  }
}
