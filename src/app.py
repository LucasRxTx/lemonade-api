from __future__ import annotations

import datetime
import logging
import os
import time

import flask
import sqlalchemy

from models import Permission, Role, User, db
from routes.auth import auth_blueprint
from routes.errors import handle_error
from routes.roles import roles_blueprint
from routes.stands import stands_blueprint
from routes.tokens import tokens_blueprint
from routes.users import users_blueprint
import services.user


logger = logging.getLogger(__name__)


def create_app() -> flask.Flask:
    # create the app
    app = flask.Flask(__name__, static_folder="static", static_url_path="/static")
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(users_blueprint)
    app.register_blueprint(tokens_blueprint)
    app.register_blueprint(stands_blueprint)
    app.register_blueprint(roles_blueprint)

    app.register_error_handler(Exception, handle_error)

    # Configure the SQLite database, relative to the app instance folder
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["SQLALCHEMY_DATABASE_URI"]
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
    app.config["JWT_ISSUER"] = os.environ["JWT_ISSUER"]
    app.config["JWT_AUDIENCE"] = os.environ["JWT_AUDIENCE"]
    app.config["JWT_ALGORITHM"] = os.environ["JWT_ALGORITHM"]

    # initialize the app with the extension
    db.init_app(app)
    with app.app_context():
        db_available = False
        backoff = 2
        retries = 4
        while not db_available:
            try:
                db.session.execute(sqlalchemy.text("SELECT 1")).scalar()
            except sqlalchemy.exc.OperationalError:
                logger.error(
                    f"Database not ready yet, {retries} retries left.  Retrying in {backoff} seconds"
                )
                time.sleep(backoff)
                backoff *= 2
                if retries - 1 > 0:
                    retries -= 1
                else:
                    logger.error(
                        f"Database not ready yet, {retries} retries left.  Killing app."
                    )
                    raise Exception(f"Database not ready after max retries")
            else:
                db_available = True

        db.drop_all()
        db.create_all()

        # add default roles and permissions
        db.session.add_all(
            [
                Role(
                    name="lemonade-stand.user",
                    permissions=[
                        Permission(name="lemonade-stand.me.get"),
                        Permission(name="lemonade-stand.my.stands.get"),
                        Permission(name="lemonade-stand.my.stands.create"),
                        Permission(name="lemonade-stand.my.stands.update"),
                        Permission(name="lemonade-stand.my.stands.delete"),
                        Permission(name="lemonade-stand.my.stands.sales.create"),
                        Permission(name="lemonade-stand.my.stands.sales.get"),
                        Permission(name="lemonade-stand.my.stands.stats.get"),
                        Permission(name="lemonade-stand.my.stands.stats.create"),
                        Permission(name="lemonade-stand.my.tokens.get"),
                    ],
                ),
                Role(
                    name="lemonade-stand.admin",
                    permissions=[
                        Permission(name="lemonade-stand.admin.users.get"),
                        Permission(name="lemonade-stand.admin.tokens.get"),
                    ],
                ),
            ]
        )

        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()
            logger.info("Only create default roles once")

        if os.environ.get("FLASK_ENV") == "development":
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            services.user.create_user(
                    email="admin@lemonadeapp.com",
                    first_name="admin",
                    last_name="admin",
                    age=99,
                    password_hash="admin",
                    roles=db.session.query(Role).all(),
                    created_at=now,
                    updated_at=now
            )
            db.session.add(
                User(
                )
            )

            try:
                db.session.commit()
            except sqlalchemy.exc.IntegrityError:
                db.session.rollback()
                logger.info("Only create admin account once")
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
