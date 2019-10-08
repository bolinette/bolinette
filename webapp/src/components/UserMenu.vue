<template>
  <v-menu offset-y>
    <template v-slot:activator="{ on }">
      <v-btn icon v-on="on">
        <v-icon v-if="loggedIn">mdi-account-circle</v-icon>
        <v-icon v-else>mdi-dots-vertical</v-icon>
      </v-btn>
    </template>

    <v-list v-if="loggedIn">
      <v-list-item @click="$router.push('account').catch(() => {})">
        <v-list-item-icon>
          <v-icon>mdi-account-box</v-icon>
        </v-list-item-icon>
        <v-list-item-title>
          Manage account
        </v-list-item-title>
      </v-list-item>
    </v-list>

    <v-divider v-if="loggedIn"/>

    <v-list>
      <v-list-item @click="toggleTheme()">
        <v-list-item-icon>
          <v-icon>mdi-invert-colors</v-icon>
        </v-list-item-icon>
        <v-list-item-title>
          Invert colors
        </v-list-item-title>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script lang="ts">
  import { Component, Vue } from 'vue-property-decorator';
  import { uiStateModule, userModule } from '@/store';
  import User from '@/models/User';

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
  }
</script>

<style lang="scss" scoped>

</style>