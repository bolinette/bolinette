import UIStateStore from '@/stores/UIStateStore';
import UserStore from '@/stores/UserStore';
import Vue from 'vue';
import Vuex from 'vuex';
import { getModule } from 'vuex-module-decorators';


Vue.use(Vuex);
const store = new Vuex.Store({
  modules: {
    ui: UIStateStore,
    user: UserStore,
  },
});
export default store;
export const userModule = getModule(UserStore, store);
export const uiStateModule = getModule(UIStateStore, store);
