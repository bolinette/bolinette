import Vue from 'vue';
import VueCookies from 'vue-cookies-ts';

Vue.use(VueCookies);


export const getCookie = (key: string): any => {
  return Vue.prototype.$cookies.get(key);
};

export const setCookie = (key: string, value: any) => {
  Vue.prototype.$cookies.set(key, value);
};
