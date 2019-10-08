import Vue from 'vue';
import App from './App.vue';
import './plugins/cookies';
import vuetify from './plugins/vuetify';
import './registerServiceWorker';
import router from './router';
import store from './store';


Vue.config.productionTip = false;
new Vue({
  router,
  store,
  vuetify,
  render: (h) => h(App),
}).$mount('#app');
