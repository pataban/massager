import flask
from flask import request, jsonify

app = flask.Flask(__name__)
app.config["DEBUG"] = True

users = {
    "qwe":[],
    "asd":[{"senderId":"qwe","msg":"hello"}],
    "zxc":[{"senderId":"qwe","msg":"heloo"},{"senderId":"asd","msg":"hi"}]
}


@app.route('/', methods=['GET','post'])
def home():
    return '''<h1>Messenge server</h1>
<p>hello</p>'''


@app.route('/api/users/all', methods=['GET'])
def api_users_all():
    return jsonify(users.keys())


@app.route('/api/users/register', methods=['POST'])      #zrobic post nie get
def api_register_user():
    # Check if an user ID was provided as part of the URL.
    # If ID is provided, assign it to a variable.
    # If no ID is provided, display an error in the browser.
    if 'id' in request.args:
        id = request.args['id']
    else:
        return "Error: No id field provided. Please specify an id."

    # If provided ID is not taken, create new user.
    # If provided ID is taken, display an error in the browser.
    if id in users:
        return "Id not available. Please select new ID"
    else:
        users[id]=[]
        return "Registered successfully"


@app.route('/api/users', methods=['GET'])
def api_user_recieve():
    if 'id' in request.args:
        id = request.args['id']
    else:
        return "Error: No id field provided. Please specify an id."

    res=users[id]
    users[id]=[]
    return jsonify(res)

@app.route('/api/send', methods=['POST'])
def api_user_send():
    if 'id' in request.args:
        id = request.args['id']
    else:
        return "Error: No id field provided. Please specify an id."

    data=request.form
    users[data["recieverId"]].append({"senderId":id,"msg":data["msg"]})
    return "message send"

@app.route('/api/send/all', methods=['POST'])
def api_user_send_everone():
    if 'id' in request.args:
        id = request.args['id']
    else:
        return "Error: No id field provided. Please specify an id."

    data=request.form
    for u in users:
        users[u].append({"senderId":id,"msg":data["msg"]})
    return "messages send"


""" 
    for book in books:
        if book['id'] == id:
            results.append(book)
    return jsonify(results)
"""
app.run()