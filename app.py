import io

from PIL import Image
from flask import Flask, jsonify, request, make_response, send_file
from flask_restful import Resource, Api, reqparse

import img_utils
import db_utils

app = Flask(__name__)
api = Api(app)


# this should serve the main frontend webpage
class Home(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('game_id', type=str, location='args', required=True, help="game_id must be provided.")

        arguments = parser.parse_args()
        game_id = arguments['game_id']

        # TODO: check if the game id is currently in database/running/etc.
        IMG_NOT_IN_DATABASE = True
        if IMG_NOT_IN_DATABASE:
            # TODO: make more helpful/better looking/etc error page
            return make_response(f"game_id {game_id} not found", 400)

        # look up the current image in the DB and return the rendered template?
        # not sure what the best way to handle this is - up to Colby


# the Noita mod sends data about the world and camera position to this endpoint, where it's saved for use by people viewing the website
class Submit(Resource):
    def post(self):
        req_json = request.json

        if 'game_id' not in req_json.keys(): # I think this can be pulled out to a decorator
            content = jsonify({"success": False, "message": "Please make sure you have all required parameters in your request"})
            return make_response(content, 400)
        
        game_id = req_json['game_id']

        ## save new camera position data
        camera_x = req_json['camera_pos']['x']
        camera_y = req_json['camera_pos']['y']
        db_utils.update_camera_position(game_id, camera_x, camera_y)

        ## save new image data
        image: Image.Image = img_utils.image_from_game_id(game_id) # see this function for database interaction

        bounds: dict = req_json['bounds']
        pixel_data: list[list[int]] = req_json['data']
        img_utils.add_terrain_to_image(image, bounds, pixel_data)

        # save image to database
        db_utils.save_image(game_id, image)

        return jsonify({"success": True})


# this endpoint returns the latest recorded camera position for a game_id given as a query param
class Camera_Info(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('game_id', type=str, location='args', required=True, help="game_id must be provided.")

        arguments = parser.parse_args()
        game_id = arguments['game_id']

        # get camera info for game_id from database
        camera_info = db_utils.get_camera_info(game_id)

        if camera_info is None:
            # TODO: make more helpful/better looking/etc error page (Colby)
            return make_response(f"game_id {game_id} not found", 400)

        response = make_response(camera_info, 200)
        response.headers['Access-Control-Allow-Origin'] = '*' # allow browsers to view response - CORS policy
        return response
    

# this endpoint should returns image data in some format for a game_id given as a query param
# right now, it's just a png that's put in an <img> tag on the frontend, but we can rework that if it makes things easier
class Terrain_Info(Resource):
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('game_id', type=str, location='args', required=True, help="game_id must be provided.")

        arguments = parser.parse_args()
        game_id = arguments['game_id']

        # get image for game_id from database
        image = db_utils.get_image(game_id)
        if image is None:
            return make_response(f"game_id {game_id} not found", 400)

        # Convert PIL Image to bytes for sending
        img_io = io.BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')


# add endpoints to Flask API
api.add_resource(Home, "/")
api.add_resource(Submit, "/submit")
api.add_resource(Camera_Info, "/info")
api.add_resource(Terrain_Info, "/terrain")

if __name__ == "__main__":
    app.run(debug=True)

