import User from '@/models/User';
import router from '@/router';
import { userModule } from '@/store';
import ApiRequest from '@/utils/ApiRequest';
import ApiResponse from '@/utils/ApiResponse';
import _ from 'lodash';
import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';


@Module({name: 'user'})
export default class UserStore extends VuexModule {
  private _currentUser: User | null = null;
  private _loadingUserInfo: boolean = true;

  public get currentUser(): User | null {
    return this._currentUser;
  }

  public get loadingUserInfo(): boolean {
    return this._loadingUserInfo;
  }

  public get loggedIn(): boolean {
    return !_.isNil(this._currentUser);
  }

  @Mutation
  public setUser(user: User | null) {
    this._currentUser = user;
  }

  @Mutation
  public loadingUserState(loading: boolean) {
    this._loadingUserInfo = loading;
  }

  @Action
  public async info() {
    userModule.loadingUserState(true);
    await new ApiRequest('/user/info', 'GET')
        .fetch<User>({
          success: (res: ApiResponse<User>) => {
            userModule.setUser(res.data);
          },
          finally: () => {
            userModule.loadingUserState(false);
          },
        });
  }

  @Action
  public async logout() {
    await new ApiRequest('/user/logout', 'POST')
        .fetch({
          success: (res: ApiResponse<string>) => {
            userModule.setUser(null);
            router.push({name: 'home'}).catch(() => '');
          },
        });
  }
}
