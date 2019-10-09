<template>
  <v-app-bar app clipped-left>
    <v-app-bar-nav-icon @click.stop="$emit('toggle-drawer')"></v-app-bar-nav-icon>

    <v-toolbar-title @click="$router.push({name:'home'}).catch((err) => {})">
      <span class="blnt-menu-title">Your Bolinette App</span>
    </v-toolbar-title>

    <div class="flex-grow-1"></div>

    <v-skeleton-loader class="loader-right-margin" type="chip" v-if="loading"></v-skeleton-loader>
    <v-skeleton-loader type="chip" v-if="loading"></v-skeleton-loader>

    <v-btn icon v-if="!loading">
      <v-icon>mdi-magnify</v-icon>
    </v-btn>

    <user-menu v-if="!loading"/>

    <v-btn @click="openLogin()" text v-if="!loading && !logged">
      Login
    </v-btn>
  </v-app-bar>
</template>

<script lang="ts">
  import UserMenu from '@/components/UserMenu.vue';
  import { uiStateModule, userModule } from '@/store';
  import { Component, Vue } from 'vue-property-decorator';


  @Component({
    components: {UserMenu},
  })
  export default class NavBar extends Vue {
    public get logged(): boolean {
      return userModule.loggedIn;
    }

    public get loading(): boolean {
      return userModule.loadingUserInfo;
    }

    public openLogin() {
      uiStateModule.setLoginForm(true);
    }
  }
</script>

<style lang="scss" scoped>
  .blnt-menu-title {
    cursor: pointer;
  }

  .blt-right-menu {
    white-space: nowrap;
  }

  .loader-right-margin {
    margin-right: 15px;
  }
</style>