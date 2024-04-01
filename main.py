import subprocess
import pandas as pd
import mysql.connector

from threading import Lock
from flask import Flask
from flask import request
from flask import send_from_directory
from flask_cors import CORS
from flask_restful import Api
from flask_restful import Resource

application = Flask(__name__)
application.config["CORS_HEADERS"] = "Content-Type"
application.config["CORS_RESOURCES"] = {r"/api/*": {"origins": "*"}}
application.config["PROPAGATE_EXCEPTIONS"] = True

CONCERTO_MYSQL_USERNAME = "root"
CONCERTO_MYSQL_PASSWORD = "imh2024"
CONCERTO_DATABASE = "database-5.0-dev"

cors = CORS(application)
api = Api(application)
export_lock = Lock()

MYSQL = {
    "host": "localhost",
    "username": "root",
    "password": "crew-scheduling123",
    "database": "concerto_export"
}


def export_sql(name, file_path):
    export_sql_command = [
        "docker", "exec", CONCERTO_DATABASE, "mysqldump",
        f"-u{CONCERTO_MYSQL_USERNAME}",
        f"-p{CONCERTO_MYSQL_PASSWORD}", "concerto", name
    ]
    result = subprocess.run(export_sql_command, capture_output=True, text=True)
    if result.returncode != 0:
        return False
    with open(file_path, "w") as f:
        f.write(result.stdout)
    return True


def import_sql(file_path):
    import_sql_command = f"mysql -u{MYSQL['username']} -p{MYSQL['password']} {MYSQL['database']} < {file_path}"
    result = subprocess.run(import_sql_command, shell=True)
    return result.returncode == 0


def create_db():
    check_db_command = f"mysql -u{MYSQL['username']} -p{MYSQL['password']} -e \"SHOW DATABASES LIKE '{MYSQL['database']}'\""
    result = subprocess.run(check_db_command, shell=True, capture_output=True, text=True)
    if MYSQL["database"] in result.stdout:
        drop_db_command = f"mysql -u{MYSQL['username']} -p{MYSQL['password']} -e \"DROP DATABASE {MYSQL['database']}\""
        subprocess.run(drop_db_command, shell=True)
    create_db_command = f"mysql -u{MYSQL['username']} -p{MYSQL['password']} -e \"CREATE DATABASE {MYSQL['database']}\""
    result = subprocess.run(create_db_command, shell=True)
    return result.returncode == 0


def read_table(name, params=None):
    cnx = mysql.connector.connect(**MYSQL)
    if params:
        condition = " AND ".join([f"{key} = %s" for key in params.keys()])
        query = f"SELECT * FROM {name} WHERE {condition}"
        df = pd.read_sql_query(query, cnx, params=list(params.values()))
    else:
        query = f"SELECT * FROM {name}"
        df = pd.read_sql_query(query, cnx)
    cnx.close()
    return df


class Index(Resource):
    def get(self):
        return send_from_directory("templates", "index.html")


class Export(Resource):
    def get(self):
        name = request.args.get("name")
        if not name:
            return {"message": "Invalid Name"}, 400
        with export_lock:
            if not export_sql(name, f"{name}_backup.sql"):
                return {"message": f"Export {name} failed"}, 500
            if not export_sql("DataTable", f"DataTable_backup.sql"):
                return {"message": "Export DataTable failed"}, 500
            if not create_db():
                return {"message": "Database creation failed"}, 500
            if not import_sql(f"{name}_backup.sql"):
                return {"message": f"Import {name} failed"}, 500
            if not import_sql("DataTable_backup.sql"):
                return {"message": f"Import DataTable failed"}, 500
        df1 = read_table(name)
        if df1.empty:
            return {"message": f"No {name} data found"}, 404
        df2 = read_table("DataTable", {"name": name})
        if df2.empty:
            return {"message": "No DataTable data found"}, 404
        updated_by = df2["updatedBy"].iloc[0]
        return {"message": "Export successfully", "updatedBy": updated_by, "records": df1.to_dict(orient="records")}, 200


api.add_resource(Index, "/", endpoint="index")
api.add_resource(Export, "/api/export", endpoint="export")


if __name__ == "__main__":
    # application.debug = True
    application.run(host="0.0.0.0", port=5057)
