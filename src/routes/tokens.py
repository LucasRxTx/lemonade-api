import flask

import services.auth
from serialization import AccessTokenResponse

tokens_blueprint = flask.Blueprint("tokens", __name__)


@tokens_blueprint.route("/my/tokens", methods=["GET"])
@services.auth.auth_required(permissions=["lemonade-stand.my.tokens.get"])
def get_all_tokens():
    tokens = services.auth.get_all_access_tokens_for_user(user_id=flask.g.user.id)
    return flask.jsonify(
        AccessTokenResponse.model_validate(token).model_dump(by_alias=True)
        for token in tokens
    )
