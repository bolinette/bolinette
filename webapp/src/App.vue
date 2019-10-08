<template>
  <v-app id="bolinette">
    <nav-bar @toggle-drawer="toggleLeftDrawer()"/>

    <drawer/>

    <login-form ref="login"/>

    <v-content>
      <router-view/>
    </v-content>

    <v-footer app>
      <span>Bolinette</span>
      <div class="flex-grow-1"></div>
      <span>&copy; 2019</span>
    </v-footer>
  </v-app>
</template>

<script lang="ts">
  import Drawer from '@/components/Drawer.vue';
  import LoginForm from '@/components/LoginForm.vue';
  import NavBar from '@/components/NavBar.vue';
  import { uiStateModule, userModule } from '@/store';
  import { Component, Vue } from 'vue-property-decorator';


  @Component({
    components: {
      Drawer,
      NavBar,
      LoginForm,
    },
  })
  export default class App extends Vue {
    public created(): void {
      userModule.info();
      uiStateModule.initTheme();
    }

    public toggleLeftDrawer() {
      uiStateModule.setLeftDrawer(!uiStateModule.leftDrawer);
    }
  }
</script>
