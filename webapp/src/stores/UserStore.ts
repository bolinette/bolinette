import User from '@/models/User';
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
  public setUser(user: User) {
    this._currentUser = user;
  }

  @Mutation
  public loadingUserState(loading: boolean) {
    this._loadingUserInfo = loading;
  }

  @Action
  public async info() {
    this.context.commit('loadingUserState', true);
    await new ApiRequest('/user/info', 'GET')
        .fetch<User>({
          success: (res: ApiResponse<User>) => {
            this.context.commit('setUser', res.data);
          },
          finally: () => {
            this.context.commit('loadingUserState', false);
          },
        });
  }
}
