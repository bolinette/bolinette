<template>
  <v-dialog max-width="750" v-model="isOpen">
    <v-card>
      <v-card-title class="headline">Log in</v-card-title>

      <v-card-text>
        <v-form v-model="valid">
          <v-text-field
            label="Username"
            required
            v-model="username"
          ></v-text-field>
          <v-text-field
            label="Password"
            required
            type="password"
            v-model="password"
          ></v-text-field>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <div class="flex-grow-1"></div>

        <v-btn @click="isOpen = false" text>
          Cancel
        </v-btn>

        <v-btn @click="login()" color="blue">
          Log in
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts">
  import User from '@/models/User';
  import { uiStateModule, userModule } from '@/store';
  import ApiRequest from '@/utils/ApiRequest';
  import { Component, Vue, Watch } from 'vue-property-decorator';


  @Component
  export default class LoginForm extends Vue {
    public valid: boolean = false;
    public loggedIn: boolean = false;
    public username: string = '';
    public password: string = '';

    public get isOpen(): boolean {
      return uiStateModule.loginForm;
    }

    public set isOpen(value: boolean) {
      uiStateModule.setLoginForm(value);
    }

    @Watch('isOpen')
    public onOpenStateChange(value: boolean): void {
      if (value) {
        this.username = '';
        this.password = '';
      } else {
        if (!this.loggedIn && uiStateModule.loginCancelCallback) {
          uiStateModule.loginCancelCallback();
        }
        uiStateModule.setLoginCallback(null);
        uiStateModule.setLoginCancelCallback(null);
      }
    }

    public login(): void {
      if (!this.valid) {
        return;
      }
      const request = new ApiRequest<any>('/user/login', 'POST');
      request.body = {
        username: this.username,
        password: this.password,
      };
      request.fetch<User>({
        success: (res) => {
          userModule.setUser(res.data);
          this.loggedIn = true;
          if (uiStateModule.loginCallback) {
            uiStateModule.loginCallback();
          }
          this.isOpen = false;
        },
        error: () => {
          this.isOpen = false;
        },
      });
    }
  }
</script>

<style lang="scss" scoped>

</style>