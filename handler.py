from flask import Flask, request, jsonify, make_response
from flask_restful import Resource, Api
from get_rtw import RightToWork

app = Flask("RTWAPI")
api = Api(app)

class RightToWorkHandler(Resource):
    def get(self):
        share_code = request.args.get('code')
        dob = request.args.get('dob')
        if not share_code or not dob:
            http_code = 400
            response = {
                "code": http_code,
                "status": "error",
                "error": "Missing required parameters", 
            }
            return make_response(jsonify(response), http_code)
        try:
            rtw = RightToWork(share_code, dob)
            http_code = 200
            response = {
                "code": http_code,
                "status": rtw.status,
                "error": None,
            }
            return make_response(jsonify(response), http_code)
        except:
            http_code = 500
            response = {
                "code": http_code,
                "status": "error",
                "error": "Something went wrong", 
            }
            return make_response(jsonify(response), http_code)
    
api.add_resource(RightToWorkHandler, '/rtw')
if __name__ == '__main__':
    app.run(debug=True)