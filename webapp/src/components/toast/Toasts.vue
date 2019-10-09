<template>
  <div class="blnt-toasts">
    <div v-for="toast of toasts">
      <toast :toast="toast"/>
    </div>
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
    position: absolute;
    bottom: 0;
    right: 25vw;
    z-index: 999;
  }
</style>