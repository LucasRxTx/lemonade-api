import unittest

import flask

from app import create_app


def get_app():
    return create_app()


class TestEndToEnd(unittest.TestCase):
    def test_end_to_end(self):
        app = get_app()
        with app.test_client() as client:
            # create user
            response = client.post(
                "/users",
                json=dict(
                    email="test.user@lemonademail.com",
                    password="password",
                    first_name="test",
                    last_name="user",
                    age=99,
                ),
            )
            self.assertEqual(response.status_code, 201)

            # login with user
            response = client.post(
                "/auth/login",
                json=dict(
                    email="test.user@lemonademail.com",
                    password="password",
                ),
            )
            self.assertEqual(response.status_code, 201)
            response_data = response.json
            self.assertIn("accessToken", response_data)
            self.assertIn("refreshToken", response_data)
            accessToken = response_data["accessToken"]
            refreshToken = response_data["refreshToken"]

            # get user
            response = client.get(
                "/users/me",
                headers={"Authorization": f"Bearer {accessToken}"},
            )
            self.assertEqual(response.status_code, 200)
            response_data = response.json
            # Have we leaded password or password_hash?
            self.assertNotIn("password", response_data)
            self.assertNotIn("password_hash", response_data)

            # get refresh token
            response = client.post(
                "/auth/refresh",
                json=dict(refreshToken=refreshToken),
            )
            self.assertEqual(response.status_code, 201)
            response_data = response.json
            self.assertIn("accessToken", response_data)
            self.assertIn("refreshToken", response_data)
            accessToken = response_data["accessToken"]
            oldRefreshToken = refreshToken
            refreshToken = response_data["refreshToken"]

            # reusing refresh token should fail
            response = client.post(
                "/auth/refresh",
                json=dict(refreshToken=oldRefreshToken),
            )
            self.assertEqual(response.status_code, 401)

            stand_lat, stand_lon = 55.594707, 13.002804
            # create a lemonade stand
            response = client.post(
                "/my/stands",
                json=dict(
                    name="test stand",
                    location=[stand_lat, stand_lon],
                    currency="USD",
                    currentPriceInMicros=1_000_000,
                ),
                headers={"Authorization": f"Bearer {accessToken}"},
            )
            self.assertEqual(response.status_code, 201)
            # get lemonade stand
            response = client.get(
                response.headers["Location"],
                headers={"Authorization": f"Bearer {accessToken}"},
            )
            print("###", response.text)
            self.assertEqual(response.status_code, 200)

            # make a sale
            stand_id = response.json["id"]
            response = client.post(
                flask.url_for("stands.sell_lemonade", stand_id=stand_id),
                json=dict(priceInMicros=1_000_000),
                headers={"Authorization": f"Bearer {accessToken}"},
            )
            self.assertEqual(response.status_code, 201)

            # get sales
            response = client.get(
                flask.url_for("stands.get_my_stand_sales", stand_id=stand_id),
                headers={"Authorization": f"Bearer {accessToken}"},
            )
            self.assertEqual(response.status_code, 200)
            print(response.json)

            # get all sales
            response = client.get(
                flask.url_for("stands.get_my_sales"),
                headers={"Authorization": f"Bearer {accessToken}"},
            )
            self.assertEqual(response.status_code, 200)
            print(response.json)

            # get current users tokens
            response = client.get(
                flask.url_for("tokens.get_all_tokens"),
                headers={"Authorization": f"Bearer {accessToken}"},
            )
            self.assertEqual(response.status_code, 200)

            # get stands near me
            response = client.get(
                flask.url_for(
                    "stands.get_stands_near_me",
                    latitude=stand_lat + 0.1,
                    longitude=stand_lon + 0.1,
                ),
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json), 1)
            print(response.json)

            # does not return stands that are too far away
            response = client.get(
                flask.url_for(
                    "stands.get_stands_near_me",
                    latitude=55.710648,
                    longitude=13.232055,
                ),
            )
            self.assertEqual(response.status_code, 200)
            print(response.json)
            self.assertEqual(len(response.json), 0)
