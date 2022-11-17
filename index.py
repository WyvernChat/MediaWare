
from io import BytesIO

import cuid
from dotenv import dotenv_values
from flask import Flask, abort, render_template, request, send_file, url_for
from PIL import Image
from pymongo import MongoClient

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8*1000*1000

image_extensions = (".gif", ".pdf", ".png", ".tiff", ".webp")

config = dotenv_values("../.env")

mongo_client = MongoClient(config["DATABASE_URL"])["wyvern-dev"]

def resize_bytes_image(image_bytes: BytesIO, size: int, format: str = "PNG"):
    photo: Image.Image = Image.open(image_bytes)
    photo = photo.resize((size, size))
    img_byte_arr = BytesIO()
    photo.save(img_byte_arr, format=format)
    return BytesIO(img_byte_arr.getvalue())

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/assets")
def create_upload():
    authorization = request.headers.get("authorization")
    if authorization == None:
        return abort(401)

    user = mongo_client["users"].find_one({
        "token": authorization
    })

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
        return abort(400)

@app.get("/assets/<id>")
def get_upload(id: str):
    is_image = id.lower().endswith(image_extensions)
    uploaded_file = mongo_client["uploads"].find_one({
        "id": id.split(".")[0] if is_image else id
    })

    if uploaded_file == None:
        return abort(404)

    file_bytes = BytesIO(uploaded_file["blob"])

    res = send_file(file_bytes, uploaded_file["type"])
    
    if is_image:
        size = int(request.args.get("size") or "128")
        # photo: Image.Image = Image.open(file_bytes)
        # photo = photo.resize((size, size))
        # img_byte_arr = BytesIO()
        # photo.save(img_byte_arr, "PNG")
        resized_image = resize_bytes_image(file_bytes, size)
        res = send_file(resized_image, uploaded_file["type"])
    res.cache_control.public = True
    res.cache_control.max_age = 300
    res.cache_control.no_cache = False
    return res


if __name__ == "__main__":
    # app.debug = True
    app.run(port=3003)
