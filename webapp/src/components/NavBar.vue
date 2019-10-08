<template>
  <v-app-bar app clipped-left>
    <v-app-bar-nav-icon @click.stop="$emit('toggle-drawer')"></v-app-bar-nav-icon>

    <v-toolbar-title @click="$router.push({name:'home'}).catch((err) => {})">
      Your Bolinette App
    </v-toolbar-title>

    <div class="flex-grow-1"></div>

    <v-skeleton-loader v-if="loading" class="loader-right-margin" type="chip"></v-skeleton-loader>
    <v-skeleton-loader v-if="loading" type="chip"></v-skeleton-loader>

    <v-btn v-if="!loading" icon>
      <v-icon>mdi-magnify</v-icon>
    </v-btn>

    <user-menu v-if="!loading"/>

    <v-btn v-if="!loading && !logged" @click="openLogin()" text>
      Login
    </v-btn>
  </v-app-bar>
</template>

<script lang="ts">
  import { Component, Vue } from 'vue-property-decorator';
  import UserMenu from '@/components/UserMenu.vue';
  import { uiStateModule, userModule } from '@/store';

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
  .blt-right-menu {
    white-space: nowrap;
  }

  .loader-right-margin {
    margin-right: 15px;
  }
</style>