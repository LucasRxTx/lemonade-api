# Frontend Developer Test

You job is to design a signup experiance for our new lemonade app.

Lemonade is an app that allows anyone to setup an account and start a real life lemonade stand.

The app will tell other users where the lemonade stand is located and how much the lemonade costs.

The lemonade stand owner can also set the price of the lemonade and see how much money they have made.

We are looking for a a bright, fresh, and modern design that will appeal to 16 - 35 year olds.

We expect our user to primarilly use the app on their mobile phones.  On future iterations we will be looking to expand the app to support desktop.


## The assignment

Use the design tool of your choice to create a design for the signup flow of the app.

- bonus points for interactive prototypes

Implement the design using the web framework of your choice.

You will be judged on:

- The quality of the design
- The quality of the code
- The overall user experience of the finished product.
- Your ability to communicate your design decisions.


## MVP

The minimum feature set we are looking for is:

- User can create an account
- User can login
- User can logout
- User can create a lemonade stand
- User can register the sale of a lemonade
- User can see a list of lemonade stands they run

bonus points for:

- User can see a list of other lemonade stands
- User can see a map of lemonade stands near them (a mock version is acceptable as the API may not be working as expected)


## The API

The API is a REST API for signing up users, handling authentication, and starting a lemonade stand.

The API server can be started with docker-compose:

```bash
docker-compose up
```

The API will be available at http://127.0.0.1:5000

Documentation for the API can be found at http://127.0.0.1:5000/static/docs.html

You can use the documentation to test the API.


### Authentication

The API uses JWT for authentication.  Look at the API documentation and find out how to generate an access token, refresh token pair.

The API is cookieless, this means you will need to pass the access token in the Authorization header of your requests.

Your header should look like this:

```
Authroization: Bearer <accessToken>
```

If your access token expires, you can get a new one by using the refresh token.  Look at the API documentation for more information on how to hand in the refresh token for a new access token.


### Authenticating with the documentation

You can use the documentation to test the API.  After creating a user, you can login with the user by clicking "Authentication" in the side bar of the documentation.

There is a field where you can paste the access token.  In this feild you can place just the token without the "Bearer" prefix.

After pasting the access token, click "Set" and you will be able to make requests to the API as the user.

