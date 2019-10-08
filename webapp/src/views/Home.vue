<template>
    <v-container class="fill-height blnt-home-container" fluid>
        <v-row align="center" justify="center">
            <v-col>
                <img v-if="dark" alt="Bolinette Logo" class="blnt-logo" src="../assets/bolinette-dark.png">
                <img v-else alt="Bolinette Logo" class="blnt-logo" src="../assets/bolinette.png">
                <h1>This is your Bolinette app!</h1>
                <div>
                    You can start working and customizing this app.
                </div>
                <div>
                    Use the Bolinette CLI to quickly build your API.
                </div>
            </v-col>
        </v-row>
    </v-container>
</template>

<script lang="ts">
  import { Component, Vue } from 'vue-property-decorator';
  import { uiStateModule } from '@/store';

  @Component
  export default class Home extends Vue {
      public get dark(): boolean {
          return uiStateModule.darkTheme;
      }
  }
</script>

<style lang="scss" scoped>
    .blnt-logo {
        max-width: 150px;
    }

    .blnt-home-container {
        text-align: center;
    }
</style>
