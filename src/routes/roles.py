import flask

from models import Permission, Role
from serialization import PermissionResponse, RoleResponse

roles_blueprint = flask.Blueprint("roles", __name__)


@roles_blueprint.route("/roles", methods=["GET"])
def get_all_roles():
    return flask.jsonify(
        RoleResponse.model_validate(role).model_dump(by_alias=True)
        for role in Role.query.all()
    )


@roles_blueprint.route("/permissions", methods=["GET"])
def get_all_permissions():
    return flask.jsonify(
        PermissionResponse.model_validate(permission).model_dump(by_alias=True)
        for permission in Permission.query.all()
    )
