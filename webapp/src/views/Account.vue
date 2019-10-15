<template>
  <v-container fluid>
    <h1>My account</h1>
    <div v-if="loading">
      <v-skeleton-loader class="mt-5" type="article"></v-skeleton-loader>
      <v-skeleton-loader class="mt-5" type="article"></v-skeleton-loader>
      <v-skeleton-loader class="mt-5" type="article"></v-skeleton-loader>
    </div>
    <div v-if="error">
      <p>You need to reenter your credentials to modify your personal info.</p>
      <p>
        <v-btn @click="loadPrivateUserInfo()">
          Log in
        </v-btn>
      </p>
    </div>
    <div v-if="!loading && !error">
      <v-card class="mt-5">
        <v-form ref="username" v-model="usernameValid">
          <v-card-title>Change your username</v-card-title>
          <v-card-text>
            <v-text-field :rules="usernameRules" label="Username"
                          required v-model="username"></v-text-field>
          </v-card-text>
          <v-card-actions>
            <v-btn :disabled="!usernameValid" @click="saveUsername()" text>Save</v-btn>
          </v-card-actions>
        </v-form>
      </v-card>
      <v-card class="mt-5">
        <v-form ref="email" v-model="emailValid">
          <v-card-title>Change your email</v-card-title>
          <v-card-text>
            <v-text-field :rules="emailRules" label="Email" required
                          type="email" v-model="email"></v-text-field>
          </v-card-text>
          <v-card-actions>
            <v-btn :disabled="!emailValid" @click="saveEmail()" text>Save</v-btn>
          </v-card-actions>
        </v-form>
      </v-card>
      <v-card class="mt-5">
        <v-form ref="password" v-model="passwordValid">
          <v-card-title>Change your password</v-card-title>
          <v-card-text>
            <v-text-field :rules="passwordRules" label="Password" required
                          type="password" v-model="password"></v-text-field>
            <v-text-field :rules="password2Rules" label="Confirm password" required
                          type="password" v-model="password2"></v-text-field>
          </v-card-text>
          <v-card-actions>
            <v-btn :disabled="!passwordValid" @click="savePassword()" text>Save</v-btn>
          </v-card-actions>
        </v-form>
      </v-card>
    </div>
  </v-container>
</template>

<script lang="ts">
  import User from '@/models/User';
  import { userModule } from '@/store';
  import ApiRequest from '@/utils/ApiRequest';
  import { Component, Vue } from 'vue-property-decorator';


  @Component
  export default class Account extends Vue {
    public $refs!: {
      username: HTMLFormElement, email: HTMLFormElement, password: HTMLFormElement,
    };
    public loading: boolean = true;
    public error: boolean = false;
    public username: string = '';
    public usernameRules: Array<(v: string) => boolean | string> = [
      (v) => !!v || 'Username is required',
      (v) => (v || '').length > 2 || 'Username must be 3 characters long',
    ];
    public usernameValid: boolean = true;
    public email: string = '';
    public emailRules: Array<(v: string) => boolean | string> = [
      (v) => !!v || 'Email is required', (v) => /.+@.+\..+/.test(v) || 'Email must be valid',
    ];
    public emailValid: boolean = true;
    public password: string = '';
    public password2: string = '';
    public passwordRules: Array<(v: string) => boolean | string> = [
      (v) => !!v || 'Password is required',
      (v) => !!v && (v || '').length > 5 || 'Password must be 6 characters long',
    ];
    public passwordValid: boolean = true;

    public get password2Rules(): Array<(v: string) => boolean | string> {
      return [
        (v) => (!!v && v) === this.password || 'Passwords must match',
      ];
    }

    public created() {
      this.loadPrivateUserInfo();
    }

    public loadPrivateUserInfo() {
      this.loading = true;
      this.error = false;
      const request = new ApiRequest('/user/me', 'GET');
      request.fetch<User>({
        success: (res) => {
          this.username = res.data.username;
          this.email = res.data.email;
          this.loading = false;
        },
        error: () => {
          this.loading = false;
          this.error = true;
        },
      });
    }

    public saveUsername() {
      if (this.$refs.username.validate()) {
        this.sendUpdate({username: this.username});
      }
    }

    public saveEmail() {
      if (this.$refs.email.validate()) {
        this.sendUpdate({email: this.email});
      }
    }

    public savePassword() {
      if (this.$refs.password.validate()) {
        this.sendUpdate({password: this.password});
      }
    }

    public sendUpdate(params: object) {
      const request = new ApiRequest<object>('/user/me', 'PUT');
      request.body = params;
      request.fetch<User>({
        success: (res) => {
          userModule.setUser(res.data);
        },
      });
    }
  }
</script>

<style lang="scss" scoped>

</style>
