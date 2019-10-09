<template>
  <div>
    <div class="blnt-error-line" v-for="error of errors">
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
  .blnt-error-line {
    color: red;
    margin-top: 10px;
  }
</style>