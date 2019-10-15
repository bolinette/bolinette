<template>
  <div>
    <div class="mt-3 red--text" v-for="error of errors">
      {{error}}
    </div>
  </div>
</template>

<script lang="ts">
  import { Component, Prop, Vue } from 'vue-property-decorator';


  @Component
  export default class FormErrors extends Vue {
    @Prop() public errors!: string[];
  }
</script>

<style lang="scss" scoped>

</style>
