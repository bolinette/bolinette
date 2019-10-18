<template>
  <v-menu offset-y transition="scroll-y-transition">
    <template v-slot:activator="{ on }">
      <v-btn icon v-on="on">
        <v-icon v-if="loggedIn">mdi-account-circle</v-icon>
        <v-icon v-else>mdi-dots-vertical</v-icon>
      </v-btn>
    </template>

    <v-list>
      <div v-if="loggedIn">
        <v-list-item @click="$router.push('account').catch(() => {})">
          <v-list-item-icon>
            <v-icon>mdi-account-box</v-icon>
          </v-list-item-icon>
          <v-list-item-title>
            Manage account
          </v-list-item-title>
        </v-list-item>
        <v-list-item @click="logout()">
          <v-list-item-icon>
            <v-icon>mdi-logout</v-icon>
          </v-list-item-icon>
          <v-list-item-title>
            Log out
          </v-list-item-title>
        </v-list-item>
        <v-divider/>
      </div>
      <div>
        <v-list-item @click="toggleTheme()">
          <v-list-item-icon>
            <v-icon>mdi-invert-colors</v-icon>
          </v-list-item-icon>
          <v-list-item-title>
            Invert colors
          </v-list-item-title>
        </v-list-item>
      </div>
    </v-list>
  </v-menu>
</template>

<script lang="ts">
  import User from '@/models/User';
  import { uiStateModule, userModule } from '@/store';
  import { Component, Vue } from 'vue-property-decorator';


  @Component
  export default class UserMenu extends Vue {
    public get loggedIn(): boolean {
      return userModule.loggedIn;
    }

    public get user(): User | null {
      return userModule.currentUser;
    }

    public toggleTheme() {
      uiStateModule.setDarkTheme(!uiStateModule.darkTheme);
    }

    public logout() {
      userModule.logout();
    }
  }
</script>

<style lang="scss" scoped>

</style>