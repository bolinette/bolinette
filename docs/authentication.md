# Users and roles

The framework comes with an authentication system with user accounts and roles.
A user is identified by its unique username.

The [`auth` middleware](./middlewares.md#authentication) can protect routes and controllers and restrict it to
certain roles.

## Authentication

The `user/login` route is the main point for a user to identify himself or herself.
This route expects a `username` and `password`.
If one user entry matches with the credentials, the API sends back two JWTs.

`access_token` is the main token that proves who the user is.
It is valid for 1 day.
That time span can be changed by the `access_token_validity` environment variable.

`refresh_token` is a backup token, valid for 30 days.
The route `user/refresh` checks this token to give a new `access_token` JWT.

If gotten from the `login` route, the access token is marked as `fresh`.
That means the requests can go through the `auth` middleware if the `fresh` option is turned on.
A refreshed token is not marked `fresh`.
This a good way to ensure the client has to enter its credentials again before accessing or modifying sensitive data.

If the environment variable `credentials` is set to `cookies`, the login route sets the tokens inside cookies and
the `auth` middleware checks inside the cookies for the tokens.
If the variable is `headers`, the tokens are sent back in the response, and the middleware checks them inside request
headers named `BLNT-ACCESS-TOKEN` and `BLNT-REFRESH-TOKEN`.

## User roles

The framework comes with two default roles.
`root` gives access to everything, bypasses all role checks in the default middlewares.
`admin` is a role meant to manage users in a Bolinette app.
This role is used in the `user` controller to control which user can add and remove roles to other users.

Admin can add roles to a user through the route `POST user/{username}/roles` and remove a role with the route
`DELETE user/{username}/roles/{role_name}`.
