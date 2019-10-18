<template>
  <v-navigation-drawer app v-model="open">
    <v-list dense>
      <v-list-item @click="$router.push({name: 'about'}).catch(() => {})">
        <v-list-item-action>
          <v-icon>mdi-help-box</v-icon>
        </v-list-item-action>
        <v-list-item-content>
          <v-list-item-title>About</v-list-item-title>
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>

<script lang="ts">
  import { uiStateModule } from '@/store';
  import { Component, Vue } from 'vue-property-decorator';


  @Component
  export default class Drawer extends Vue {
    public get open(): boolean {
      return uiStateModule.leftDrawer;
    }

    public set open(value: boolean) {
      uiStateModule.setLeftDrawer(value);
    }
  }
</script>

<style lang="scss" scoped>

</style>
