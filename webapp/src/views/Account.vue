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
          <v-text-field v-model="username" label="First name" required></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn text @click="saveUsername()">Save</v-btn>
        </v-card-actions>
      </v-card>
      <v-card class="top-margin">
        <v-card-title>Change your email</v-card-title>
        <v-card-text>
          <v-text-field v-model="email" label="Email" type="email" required></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn text @click="saveEmail()">Save</v-btn>
        </v-card-actions>
      </v-card>
      <v-card class="top-margin">
        <v-card-title>Change your password</v-card-title>
        <v-card-text>
          <v-text-field v-model="password" label="Password" :error-messages="passwordErrors"
                        type="password" required @change="checkPassword"></v-text-field>
          <v-text-field v-model="password2" label="Confirm password"
                        type="password" required @change="checkPassword"></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn text @click="savePassword()">Save</v-btn>
        </v-card-actions>
      </v-card>
    </div>
  </v-container>
</template>

<script lang="ts">
  import { Component, Vue } from 'vue-property-decorator';
  import ApiRequest from '@/utils/ApiRequest';
  import User from '@/models/User';
  import { userModule } from '@/store';

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