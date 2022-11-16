
import werkzeug
from werkzeug.utils import import_string

werkzeug.import_string = import_string

from io import BytesIO

import cuid
import cv2
import numpy as np
from dotenv import dotenv_values
from flask import Flask, abort, request, send_file, url_for
from PIL import Image
# from flask_cache import Cache
from pymongo import MongoClient

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8*1000*1000

# cache = Cache(config={"CACHE_TYPE": "simple"})

config = dotenv_values("../.env")

mongo_client = MongoClient(config["DATABASE_URL"])["wyvern-dev"]

def resize_bytes_image(image_bytes: BytesIO):
    size = int(request.args.get("size")) or 128
    photo: Image.Image = Image.open(image_bytes)
    photo = photo.resize((64, 64))
    img_byte_arr = BytesIO()
    photo.save(img_byte_arr, "PNG")
    return BytesIO(img_byte_arr.getvalue())
    # return send_file(BytesIO(img_byte_arr.getvalue()), uploaded_file["type"]) 

@app.post("/assets")
def create_upload():
    authorization = request.headers.get("authorization")
    if authorization == None:
        return abort(401)

    user = mongo_client["users"].find_one({
        "token": authorization
    })

    # print(request.files)
    if "file" not in request.files:
        return abort(400)

    file = request.files["file"]
    if file.filename != None:
        blob = file.stream.read()
        id = cuid.cuid()
        mongo_client["uploads"].insert_one({
            "name": file.filename,
            "type": file.mimetype,
            "id": id,
            "author": user["id"],
            "blob": blob
        })
        return {
            "name": file.filename,
            "type": file.mimetype,
            "id": id,
            "author": user["id"],
            "url": url_for("get_upload", id=id)
        }
    else:
        print("not in form")
        return abort(400)

@app.get("/assets/<id>")
# @cache.cached(timeout=300)
def get_upload(id):
    uploaded_file = mongo_client["uploads"].find_one({
        "id": id
    })

    if uploaded_file == None:
        return abort(404)

    file_bytes = BytesIO(uploaded_file["blob"])

    res = send_file(file_bytes, uploaded_file["type"])
    
    if uploaded_file["type"].startswith("image/"):
        size = int(request.args.get("size") or "128")
        photo: Image.Image = Image.open(file_bytes)
        photo = photo.resize((size, size))
        img_byte_arr = BytesIO()
        photo.save(img_byte_arr, "PNG")
        res = send_file(BytesIO(img_byte_arr.getvalue()), uploaded_file["type"])
    res.cache_control.public = True
    res.cache_control.max_age = 300
    return res


if __name__ == "__main__":
    # app.debug = True
    app.run(port=3003)
