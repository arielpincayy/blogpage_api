from flask import Flask, g, jsonify, request
from flask_cors import CORS
import sqlite3
from firebase_admin import credentials, auth, initialize_app
from datetime import datetime

app = Flask(__name__)
CORS(app)

cred = credentials.Certificate('myownnotesuwu-firebase-adminsdk-fdu80-a26f407557.json')
initialize_app(cred)


DATABASE = 'database/blogs.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/', methods=['GET'])
def get_init():
    response = {
        'message': 'Holiii mamahvo'
    }
    return jsonify(response),200


@app.route('/blogsTitles', methods=['GET'])
def get_blogs():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM blog_titles')
    blogs_titles = cursor.fetchall()
    blogs_list = [{'user_id': row[0], 'blog_id': row[1], 'title': row[2], 'date': row[3], 'key_words': row[4]} for row in blogs_titles]
    return jsonify(blogs_list)

@app.route('/blog/<int:blogid>/<string:uid>', methods=['GET'])
def get_blog(blogid,uid):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
                       SELECT title,date,key_words FROM blog_titles WHERE blog_id=? AND user_id=?
                       """,(blogid,uid))
        h = cursor.fetchone()
        header = {'title':h[0],'date':h[1], 'keywords':h[2].split(",")}
        cursor.execute("""
                       SELECT pos,content,type FROM blogs_content WHERE blog_id=?
                       """,(blogid,))
        c = cursor.fetchall()
        content = [{'pos':x[0],'content':x[1].split("\n") if x[2]=='Text' else x[1],'type':x[2]} for x in c]

        if header is None:
            return jsonify({'error':'Data not found'})
        
        return jsonify({'header':header, 'body':content})
    except Exception as e:
        return jsonify({'error':str(e)})

@app.route('/createBlogPage', methods=['POST'])
def post_blog():
    response = request.json
    date = datetime.now().strftime("%B %d, %Y")
    user_id = response['user']['uid']
    title = response['blog']['title']
    keywords = response['blog']['keywords']
    body = response['blog']['body']
    
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO blog_titles (user_id, title, date, key_words) VALUES (?, ?, ?, ?)', (user_id, title, date, keywords))
        id_blog = cursor.lastrowid
        blog_content = [(i,id_blog,"\n".join(body[str(i)]['cont']['content']) if body[str(i)]['cont']['sel'] == 'Text' else body[str(i)]['cont']['content'],body[str(i)]['cont']['sel'])
    for i in range(len(body))]
        cursor.executemany('INSERT INTO blogs_content (pos, blog_id, content, type) VALUES (?, ?, ?, ?)',blog_content)
        db.commit()
        return jsonify({'message': 'Success'})
    except Exception as e:
        return jsonify({'error':str(e)})
    

@app.route('/session', methods=['POST'])
def init_session():
    id_token = request.headers.get('Authorization')

    if not id_token:
        return jsonify({'error': 'No token provided or Invalid token'}), 401

    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        name = decoded_token['name']
        email = decoded_token['email']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT 1 FROM users WHERE user_id == ?', (uid,))
        exists = cursor.fetchone() is not None
        
        if not exists:
            cursor.execute('INSERT INTO users (name, user_id, email) VALUES (?, ?, ?)', (name, uid, email))
            print('User created')
            db.commit()
        
        
        return jsonify({'uid': uid, 'name': name, 'email': email}), 200
    except Exception as e:
        return jsonify({'error': str(e) }), 401

if __name__ == '__main__':
    app.run(debug=True)
