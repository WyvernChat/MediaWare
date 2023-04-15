import re
from io import BytesIO
from typing import List, Union

import cuid
import httpx
from dotenv import dotenv_values
from flask import Flask, abort, render_template, request, send_file, url_for
from flask_cors import CORS
from PIL import Image
from pymongo import MongoClient
from pymongo.collection import Collection

from upload import ImageSize, Upload
from user import User
from utils import list_find

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1000 * 1000

CORS(app)

image_formats = ("GIF", "PNG", "TIFF", "WEBP")

image_types = ("image/gif", "image/png", "image/tiff", "image/webp")

image_sizes = (20, 40, 60, 80, 100, 160, 240, 300, 320, 480, 600, 640)

config = dotenv_values(".env")

mongo_client = MongoClient(config["DATABASE_URL"])["wyvern-dev"]

image_regex = re.compile(
    r"^c[a-z0-9]{21,29}\.(" + "|".join(image_formats).lower() + r")$",
    re.MULTILINE | re.IGNORECASE,
)


def resize_bytes_image(image_bytes: BytesIO, size: int, image_format: str = "PNG"):
    photo: Image.Image = Image.open(image_bytes)
    photo = photo.resize((size, size))
    img_byte_arr = BytesIO()
    print(image_format)
    photo.save(img_byte_arr, format=image_format)
    return BytesIO(img_byte_arr.getvalue())


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/assets")
def create_upload():
    authorization = request.headers.get("authorization")
    if authorization == None:
        return abort(401)

    usersCollection: Collection[User] = mongo_client["users"]
    user = usersCollection.find_one({"token": authorization})

    if user == None:
        print("no user")
        return abort(403)

    if "file" not in request.files:
        print("no file")
        return abort(400)

    file = request.files["file"]
    if file.filename != None:
        print("filename found")
        is_image = file.mimetype in image_types
        blob = file.stream.read()
        id = cuid.cuid()
        uploadsCollection: Collection[Upload] = mongo_client["uploads"]

        if is_image:
            print("is image")
            resized: List[ImageSize] = []
            for size in image_sizes:
                print(f"resizing {size}")
                for format in image_formats:
                    print(f"in format {format}")
                    resized.append(
                        {
                            "size": size,
                            "blob": resize_bytes_image(
                                BytesIO(blob),
                                size,
                                file.filename.split(".")[-1]
                                if "." in file.filename
                                else "PNG",
                            ).getvalue(),
                            "format": format,
                        }
                    )
            print(f"resized: {len(resized)}")
            uploadsCollection.insert_one(
                {
                    "name": file.filename,
                    "type": file.mimetype,
                    "id": id,
                    "author": user["id"],
                    "blob": blob,
                    "sizes": resized,
                }
            )
        else:
            print("is not image")
            uploadsCollection.insert_one(
                {
                    "name": file.filename,
                    "type": file.mimetype,
                    "id": id,
                    "author": user["id"],
                    "blob": blob,
                }
            )
        return {
            "name": file.filename,
            "type": file.mimetype,
            "id": id,
            "author": user["id"],
            "url": url_for("get_upload", id=id),
        }
    else:
        print("no filename")
        return abort(400)


@app.get("/assets/<id>")
def get_upload(id: str):
    is_image = bool(image_regex.search(id))
    uploaded_file: Union[Upload, None] = None

    collection: Collection[Upload] = mongo_client["uploads"]

    if not is_image:
        print("is not image")
        uploaded_file = collection.find_one({"id": id})
    else:
        print("is image")
        print(id.split(".")[0])
        uploaded_file = collection.find_one({"id": id.split(".")[0]})

    if uploaded_file == None:
        print("found none")
        return abort(404)

    if not uploaded_file["sizes"]:
        print("sizes not found")
        file_bytes = BytesIO(uploaded_file["blob"])
    else:
        size = request.args.get("size") or 160
        image = list_find(
            uploaded_file["sizes"],
            lambda s: s["format"] == id.split(".")[1] and s["size"] == size,
        )
        print(f"image: {bool(image)}")
        file_bytes = BytesIO((image or uploaded_file)["blob"])

    res = send_file(file_bytes, uploaded_file["type"])

    res.cache_control.public = True
    res.cache_control.max_age = 300
    res.cache_control.no_cache = False
    return res


@app.get("/proxy/<path:source_url>")
def get_proxy(source_url):
    if source_url == None:
        return abort(404)

    r = httpx.get(source_url)
    return r.content


if __name__ == "__main__":
    # app.debug = True
    app.run(port=3003)
