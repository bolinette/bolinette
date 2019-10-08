<template>
  <v-container fluid>
    <h1>My account</h1>
    <div v-if="loading">
      <v-skeleton-loader class="top-margin" type="article"></v-skeleton-loader>
      <v-skeleton-loader class="top-margin" type="article"></v-skeleton-loader>
      <v-skeleton-loader class="top-margin" type="article"></v-skeleton-loader>
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
      <v-card class="top-margin">
        <v-card-title>Change your username</v-card-title>
        <v-card-text>
          <v-text-field label="First name" required v-model="username"></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn @click="saveUsername()" text>Save</v-btn>
        </v-card-actions>
      </v-card>
      <v-card class="top-margin">
        <v-card-title>Change your email</v-card-title>
        <v-card-text>
          <v-text-field label="Email" required type="email" v-model="email"></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn @click="saveEmail()" text>Save</v-btn>
        </v-card-actions>
      </v-card>
      <v-card class="top-margin">
        <v-card-title>Change your password</v-card-title>
        <v-card-text>
          <v-text-field :error-messages="passwordErrors" @change="checkPassword" label="Password"
                        required type="password" v-model="password"></v-text-field>
          <v-text-field @change="checkPassword" label="Confirm password"
                        required type="password" v-model="password2"></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn @click="savePassword()" text>Save</v-btn>
        </v-card-actions>
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
    public loading: boolean = true;
    public error: boolean = false;
    public username: string = '';
    public email: string = '';
    public password: string = '';
    public password2: string = '';
    public passwordErrors: string[] = [];

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

    public checkPassword() {
      if (this.password === this.password2) {
        this.passwordErrors = [];
      } else {
        this.passwordErrors = ['Passwords don\'t match'];
      }
    }

    public saveUsername() {
      this.sendUpdate({username: this.username});
    }

    public saveEmail() {
      this.sendUpdate({email: this.email});
    }

    public savePassword() {
      if (this.passwordErrors.length === 0) {
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
  .top-margin {
    margin-top: 15px;
  }
</style>