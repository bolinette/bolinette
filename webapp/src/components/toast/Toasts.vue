<template>
  <div class="blnt-toasts">
    <v-scroll-y-reverse-transition group>
      <div v-for="toast of toasts" :key="toast.id">
          <toast :toast="toast"/>
      </div>
  </v-scroll-y-reverse-transition>
  </div>
</template>

<script lang="ts">
  import Toast from '@/components/toast/Toast.vue';
  import ToastData from '@/data/ToastData';
  import { toastModule } from '@/store';
  import { Component, Vue } from 'vue-property-decorator';


  @Component({
    components: {
      Toast,
    },
  })
  export default class Toasts extends Vue {
    public get toasts(): ToastData[] {
      return toastModule.toasts;
    }
  }
</script>

<style lang="scss" scoped>
  .blnt-toasts {
    width: 50vw;
    position: fixed;
    bottom: 0;
    right: 25vw;
    z-index: 999;
  }
</style>