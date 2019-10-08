<template>
  <v-navigation-drawer app clipped v-model="open">
    <v-list dense>
      <v-list-item>
        <v-list-item-action>
          <v-icon>mdi-settings</v-icon>
        </v-list-item-action>
        <v-list-item-content>
          <v-list-item-title>Option</v-list-item-title>
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>

<script lang="ts">
  import { Component, Vue } from 'vue-property-decorator';
  import { uiStateModule } from '@/store';

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
