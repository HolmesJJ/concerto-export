import subprocess

from flask import Flask
from flask import request
from flask_cors import CORS
from flask_restful import Api
from flask_restful import Resource

application = Flask(__name__)
application.config["CORS_HEADERS"] = "Content-Type"
application.config["CORS_RESOURCES"] = {r"/api/*": {"origins": "*"}}
application.config["PROPAGATE_EXCEPTIONS"] = True

CONCERTO_MY_SQL_USERNAME = "root"
CONCERTO_MY_SQL_PASSWORD = "imh2024"
CONCERTO_DATABASE = "database-5.0-dev"


cors = CORS(application)
api = Api(application)


class Index(Resource):
    def get(self):
        return "Hello World"


class Export(Resource):
    def get(self):
        name = request.args.get("name")
        if not name:
            return {"message": "Invalid Name"}, 400
        command = [
            "docker", "exec", CONCERTO_DATABASE, "mysqldump",
            f"-u{CONCERTO_MY_SQL_USERNAME}",
            f"-p{CONCERTO_MY_SQL_PASSWORD}", "concerto", name
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            with open(f"{name}_backup.sql", "w") as f:
                f.write(result.stdout)
            return {"message": "Export successfully"}, 200
        else:
            return {"message": "Export failed"}, 400


api.add_resource(Index, "/", endpoint="index")
api.add_resource(Export, "/api/export", endpoint="export")


if __name__ == "__main__":
    # application.debug = True
    application.run(host="0.0.0.0", port=5057)
