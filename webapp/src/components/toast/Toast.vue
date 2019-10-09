<template>
  <v-alert :type="toast.type" dismissible>
    {{toast.message}}
  </v-alert>
</template>

<script lang="ts">
  import ToastData from '@/data/ToastData';
  import { Component, Prop, Vue } from 'vue-property-decorator';


  @Component
  export default class Toast extends Vue {
    @Prop() public toast!: ToastData;
  }
</script>

<style lang="scss" scoped>

</style>