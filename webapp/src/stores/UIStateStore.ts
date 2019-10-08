import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';

import vuetify from '@/plugins/vuetify';
import { getCookie, setCookie } from '@/plugins/cookies';

@Module({name: 'ui'})
export default class UIStateStore extends VuexModule {
  private _loginForm: boolean = false;
  private _loginCallback: (() => void) | null = null;
  private _loginCancelCallback: (() => void) | null = null;
  private _darkTheme: boolean = false;
  private _leftDrawer: boolean = false;

  public get darkTheme(): boolean {
    return this._darkTheme;
  }

  @Mutation
  public setDarkTheme(value: boolean) {
    this._darkTheme = value;
    vuetify.framework.theme.dark = value;
    setCookie('blnt-theme', value ? 'dark' : 'light');
  }

  @Action
  public initTheme() {
    const theme = getCookie('blnt-theme');
    if (theme) {
      this.context.commit('setDarkTheme', theme === 'dark');
    } else {
      setCookie('blnt-theme', 'light');
    }
  }

  public get loginForm(): boolean {
    return this._loginForm;
  }

  @Mutation
  public setLoginForm(value: boolean) {
    this._loginForm = value;
  }

  public get loginCallback(): (() => void) | null {
    return this._loginCallback;
  }

  @Mutation
  public setLoginCallback(callback: (() => void) | null) {
    this._loginCallback = callback;
  }

  public get loginCancelCallback(): (() => void) | null {
    return this._loginCancelCallback;
  }

  @Mutation
  public setLoginCancelCallback(callback: (() => void) | null) {
    this._loginCancelCallback = callback;
  }

  public get leftDrawer(): boolean {
    return this._leftDrawer;
  }

  @Mutation
  public setLeftDrawer(value: boolean) {
    this._leftDrawer = value;
  }
}
