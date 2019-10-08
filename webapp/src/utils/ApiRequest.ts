import _ from 'lodash';

import Env from '@/utils/Env';
import ApiResponse from '@/utils/ApiResponse';
import { uiStateModule } from '@/store';
import { getCookie } from '@/plugins/cookies';

export default class ApiRequest<T> {
  private readonly _method: string;

  private readonly _path: string;

  private _body: T | null;

  public constructor(path: string, method: string) {
    this._path = path;
    this._method = method;
    this._body = null;
  }

  public get body(): T | null {
    return this._body;
  }

  public set body(body: T | null) {
    this._body = body;
  }

  public get method(): string {
    return this._method;
  }

  public get path(): string {
    return this._path;
  }

  public async fetch<R>(params: Partial<FetchParams<R>>) {
    let body = null;
    const headers = new Headers({
      Accept: 'application/json',
    });
    const token = getCookie('csrf_access_token');
    if (token) {
      headers.set('X-CSRF-TOKEN', token);
    }
    if (this._body !== null) {
      if (this._body instanceof File) {
        body = new FormData();
        body.append('file', this._body);
      } else {
        body = JSON.stringify(this._body);
        headers.set('Content-Type', 'application/json');
      }
    }
    await this.doFetch<R>(body, headers, params);
  }

  private async refreshToken<R>(params: Partial<FetchParams<R>>, errors: string[]) {
    const token = getCookie('csrf_refresh_token');
    if (_.isNil(token)) {
      return params.error && params.error(errors);
    }
    const headers = new Headers({
      'Accept': 'application/json',
      'X-CSRF-TOKEN': token,
    });
    const refreshRequest = new ApiRequest('/user/token/refresh', 'POST');
    await refreshRequest.doFetch(null, headers, {
      refresh: false,
      success: () => {
        this.fetch(params);
      },
    });
  }

  private async doFetch<R>(body: string | FormData | null, headers: Headers, params: Partial<FetchParams<R>>) {
    const init: object = {
      body,
      credentials: 'include',
      headers,
      method: this._method,
      mode: 'cors',
    };
    let doFinally = true;
    try {
      const fetchResponse = await fetch(new Request(Env.API_URL + this._path, init), init);
      const response = await fetchResponse.json() as ApiResponse<R>;
      if (Math.floor(response.code / 100) !== 2) {
        if (response.messages.includes('user.token.expired') &&
            (params.refresh === undefined || params.refresh)) {
          await this.refreshToken(params, response.messages);
          doFinally = false;
        } else if (response.messages.includes('user.token.fresh_required') &&
            (params.openLogin === undefined || params.openLogin)) {
          doFinally = false;
          uiStateModule.setLoginCallback(() => {
            this.fetch(params);
          });
          uiStateModule.setLoginCancelCallback(() => {
            if (params.error) {
              params.error([]);
            }
          });
          uiStateModule.setLoginForm(true);
        } else if (params.error) {
          params.error(response.messages);
        }
      } else if (params.success) {
        params.success(response);
      }
    } catch (e) {
      if (params.error) {
        params.error([e]);
      }
    }
    if (params.finally && doFinally) {
      params.finally();
    }
  }
}

export interface FetchParams<T> {
  error: (errors: string[]) => void;

  finally: () => void;

  openLogin: boolean;

  refresh: boolean;

  success: (res: ApiResponse<T>) => void;
}
