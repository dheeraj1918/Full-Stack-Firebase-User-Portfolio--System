from flask import *
import requests
import pyrebase
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from api import auth_config,db_config

app=Flask(__name__, template_folder='templates')
app.secret_key="My_Key"

firebase=pyrebase.initialize_app(auth_config)
firebase_auth=firebase.auth()

firebase_db=pyrebase.initialize_app(db_config)
db=firebase_db.database()
storage=firebase_db.storage()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login_signup_search')
def login_signup_search():
    return render_template('login_signup_search.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        user_email=request.form['user_email']
        user_password=request.form['user_password']
        try:
            user_info=firebase_auth.sign_in_with_email_and_password(user_email,user_password)
            account_info=firebase_auth.get_account_info(user_info['idToken'])
            if not  account_info['users'][0]['emailVerified']:
                unverified_message="Please verify your email"
                return render_template('login.html',unverified_message=unverified_message)
            session['idToken']=user_info['idToken']
            session['email']=account_info['users'][0]['email']
            session['uid']=account_info['users'][0]['localId']
            return redirect(url_for('dashboard'))
        except Exception as e:
            print(f"Error {e}")
            unSuccess="Please verify your credientials"
            return render_template('login.html',unSuccess=unSuccess)
    if 'idToken' not in session:
        return render_template('login.html')
    return render_template('login.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        user_username=request.form['user_username']
        user_email=request.form['user_email']
        user_password0=request.form['user_password0']
        user_password1=request.form['user_password1']
        if user_password0==user_password1:
            all_users=db.child('users').get().val()
            if all_users:
                for uid,data in all_users.items():
                    if data.get('username')==user_username:
                        exist_message = "Username already taken"
                        return render_template('signup.html', exist_message=exist_message)
            
            try:
                newuser=firebase_auth.create_user_with_email_and_password(user_email,user_password0)
                uid=newuser['localId']
                user_data={
                    'email':user_email,
                    'username':user_username,
                }
                db.child('users').child(uid).set(user_data)
                db.child('users_username').child(uid).set(user_data)
                firebase_auth.send_email_verification(newuser['idToken'])
                return render_template('verify.html')
            except:
                exist_message="this email is already used"
                return render_template('signup.html',exist_message=exist_message)
    return render_template('signup.html')

@app.route('/forgotpassword',methods=['GET','POST'])
def forgotpassword():
    if request.method=='POST':
        email=request.form['email']
        firebase_auth.send_password_reset_email(email)
        return redirect('/login')
    return render_template('forgotpassword.html')
    

@app.route('/dashboard')
def dashboard():
    if 'idToken' not in session:
        return redirect(url_for('login'))
    uid = session.get('uid')
    user_data = db.child("users").child(uid).get().val()
    error_message=""
    if not user_data:
        user_data = {}
    try:
        # Get profile photo URL
        user_data['photo_url'] = storage.child(f"user_images/{uid}.jpg").get_url(None)
    except:
        user_data['photo_url'] = ""

    try:
        # Get resume URL
        user_data['resume_url'] = storage.child(f"resumes/{uid}.pdf").get_url(None)
    except:
        error_message="Please upload your resume"
        user_data['resume_url'] = ""

    return render_template('dashboard.html', user=user_data,message=error_message)

@app.route('/file/home')
def home():
    if 'idToken' not in session:
        return redirect(url_for('login'))
    uid=session.get('uid')
    try:
        user_data=db.child('users').child(uid).get().val()
        education_data=db.child('education').child(uid).get().val()
        return render_template("home.html",userdata=user_data,education_data=education_data)
    except:
        return "something went wrong"
    
@app.route('/file/edit', methods=['GET', 'POST'])
def edit():
    if 'idToken' not in session:
        return redirect(url_for('login'))
    uid = session.get('uid')

    if request.method == 'POST':
        user_name = request.form['user_username']
        email = request.form['user_email']
        about = request.form['user_about']
        github = request.form['github_link']
        linkedin = request.form['linkedin_link']

        user_data = {
            "name": user_name,
            "email": email,
            "about": about,
            "github": github,
            "linkedin": linkedin,
        }

        db.child("users").child(uid).update(user_data)
        return redirect(url_for('dashboard'))

    # GET request
    try:
        user_data = db.child("users").child(uid).get().val()
    except:
        user_data = None

    if user_data is None:
        user_data = {
            "name": "",
            "email": session.get("email", ""),
            "about": "",
            "github": "",
            "linkedin": "",
        }

    return render_template("edit.html", user=user_data)

@app.route('/file/education',methods=['GET','POST'])
def education():
    if 'idToken' not in session:
        return redirect(url_for('login'))
    uid=session.get('uid')
    if request.method=='POST':
        user_college=request.form['user_college']
        user_degree=request.form['user_degree']
        user_batch=request.form['user_batch']
        user_batch_complete=request.form['user_batch_complete']
        user_skills=request.form.getlist('skills[]')

        user_education={
            "college":user_college,
            "degree":user_degree,
            "batch":user_batch,
            "batch_complete":user_batch_complete,
            "skills":user_skills,
        }
        db.child("education").child(uid).update(user_education)
        return redirect(url_for('dashboard'))
    try:
        user_education=db.child("education").child(uid).get().val()
    except:
        user_education=None
    if user_education is None:
        user_education={
            "college":"",
            "degree":"",
            "batch":"",
            "batch_complete":"",
            "skills":"",
        }
    return render_template('education.html',user_education=user_education)

@app.route('/file/about',methods=['GET','POST'])
def about():
    if 'idToken' not in session:
        return redirect(url_for('login'))
    uid = session.get('uid')
    user_data = db.child("users").child(uid).get().val()
    return render_template('about.html',user_data=user_data)

@app.route('/file/github')
def github():
    if 'idToken' not in session:
        return redirect(url_for('login'))

    uid = session.get('uid')
    user_data = db.child("users").child(uid).get().val()
    if not user_data:
        user_data = {}

    github_id = user_data.get('github', '')
    
    repos = []
    if github_id:
        url = f"https://api.github.com/users/{github_id}/repos"
        response = requests.get(url)
        if response.status_code == 200:
            repos = response.json()

    return render_template('github.html', username=user_data.get('name', 'User'), repos=repos)


@app.route('/file/linkedin')
def linkedin():
    if 'idToken' not in session:
        return redirect(url_for('login'))
    uid=session.get('uid')
    user_data = db.child("users").child(uid).get().val()
    if not user_data:
        user_data = {}
    linkedin=user_data.get('linkedin','')
    url=f"https://www.linkedin.com/in/{linkedin}"
    return render_template('linkedin.html',linkedin=url)
@app.route('/file/user_resume',methods=['GET','POST'])
def user_resume():
    uid=session.get('uid')
    user_data = db.child("users").child(uid).get().val()
    if not user_data:
        user_data = {}

    if request.method=="POST":
        user_resume=request.files['user_resume']
        storage.child(f"resumes/{uid}.pdf").put(user_resume)
        return redirect(url_for('dashboard'))
    
    try:
        resume_path = f"resumes/{uid}.pdf"
        resume_url = storage.child(resume_path).get_url(None)

        # Optional: verify if actually exists (needs `requests`)
        import requests
        test = requests.get(resume_url)
        if test.status_code != 200:
            resume_url = ""
    except:
        resume_url = ""

    user_data['resume_url'] = resume_url
    return render_template('resume.html', user=user_data)

@app.route('/file/user_photo',methods=['GET','POST'])
def user_photo():
    uid = session.get('uid')
    if request.method == "POST":
        
        user_photo = request.files.get('user_photo')

        # Validate: check if file was uploaded
        if not user_photo or user_photo.filename == '':
            return "No file selected", 400

        # Optional: check if it's an image by MIME type
        if not user_photo.content_type.startswith('image/'):
            return "Only image files are allowed", 400

        try:
            # Open and convert to RGB
            image = Image.open(user_photo)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Save as JPEG in memory
            buffer = BytesIO()
            image.save(buffer, format='JPEG')
            buffer.seek(0)

            # Upload to Firebase Storage
            storage.child(f"user_images/{uid}.jpg").put(buffer)

            return redirect(url_for('dashboard'))

        except UnidentifiedImageError:
            return "Invalid image file", 400
    # user_photo_url = storage.child(f"resumes/{uid}.pdf").get_url(None)
    return render_template('dashboard.html')

@app.route('/search_user',methods=['GET','POST'])
def search_user():
    if request.method=='POST':
        search_user=request.form['search_user']
        all_users=db.child('users_username').get().val()
        if not all_users:
            return render_template('getusername.html', notfound_message="No users found")
        matched_user=None
        matched_uid=None
        flag=False
        for uid,data in all_users.items():
            if data.get('username','').lower()==search_user:
                matched_user=data
                matched_uid=uid
                flag=True
                print(all_users)
                print(matched_user)
                break
        if flag:
            if matched_user:
                photo_url=storage.child(f'user_images/{matched_uid}.jpg').get_url(None)
                try:
                    if requests.get(photo_url).status_code==200:
                        matched_user['photo_url']=photo_url
                    else:
                        matched_user['photo_url']=""
                except:
                    matched_user['photo_url']=""
                session['uid']=matched_uid
                return render_template('searchuser_dashboard.html',search_user=matched_user)
        elif flag==False:
            notfound_message="user not found"
            return render_template('getusername.html',notfound_message=notfound_message)
    return render_template('getusername.html')

@app.route('/file/searchuser_home')
def searchuser_home():
    uid = request.args.get('uid')
    try:
        user_data=db.child("users").child(uid).get().val()
        education_data=db.child('education').child(uid).get().val()
        print("user data" ,user_data)
        print("education data ",education_data)
        return render_template('searchuser_home.html',userdata=user_data,education_data=education_data)
    except:
        user_data=None
    return "something went wrong"

@app.route('/file/searchuser_about')
def searchuser_about():
    uid = request.args.get('uid')
    try:
        user_data=db.child("users").child(uid).get().val()
        return render_template('searchuser_about.html',userdata=user_data)
    except:
        user_data=None
    return "something went wrong"

@app.route('/file/searchuser_github')
def searchuser_github():
    uid = request.args.get('uid')
    user_data = db.child("users").child(uid).get().val()
    if not user_data:
        user_data = {}
    github_id = user_data.get('github', '')
    
    repos = []
    if github_id:
        url = f"https://api.github.com/users/{github_id}/repos"
        response = requests.get(url)
        if response.status_code == 200:
            repos = response.json()

    return render_template('searchuser_github.html', username=user_data.get('name', 'User'), repos=repos)

@app.route('/file/searchuser_linkedin')
def searchuser_linkedin():
    uid = request.args.get('uid')
    user_data = db.child("users").child(uid).get().val()
    if not user_data:
        user_data = {}
    linkedin=user_data.get('linkedin','')
    url=f"https://www.linkedin.com/in/{linkedin}"
    return render_template('searchuser_linkedin.html',linkedin=url)

@app.route('/file/searchuser_resume')
def searchuser_resume():
    uid = request.args.get('uid')
    user_data = db.child("users").child(uid).get().val()
    try:
        resume_path = f"resumes/{uid}.pdf"
        resume_url = storage.child(resume_path).get_url(None)

        # Optional: verify if actually exists (needs `requests`)
        import requests
        test = requests.get(resume_url)
        if test.status_code != 200:
            resume_url = ""
    except:
        resume_url = ""

    user_data['resume_url'] = resume_url
    return render_template('resume.html', user=user_data)

@app.route('/file/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__=="__main__":
    app.run(debug=True,port=1918)