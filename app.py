#import statements
import flask, json, requests, time, _thread, os, youtube_dl, sqlite3, datetime, flask_session, random, pip, shutil, hashlib
import urllib.parse as URLLIB_PARSE
import werkzeug.security as WZS

#make a connection to the database
DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

#the default directory for the videos to be downloaded to
DEFAULT_VIDEO_DOWNLOAD_DIR = DATABASE_CURSOR.execute('SELECT config_data_content FROM app_config WHERE config_data_title = ?', ('DEFAULT_DOWNLOAD_DIR',)).fetchall()[0][0]

#the valid video formats
validVideoFormats = ['aac', 'flac', 'mp3', 'm4a', 'opus', 'vorbis', 'wav', 'bestaudio', 'mp4', 'flv', 'webm', 'ogg', 'mkv', 'avi', 'bestvideo', 'best', 'ultra']

#create the application class
app = flask.Flask(__name__)

#set up session handling
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
flask_session.Session(app)

#set up the directory tree
app._static_folder = './static'
app.template_folder = './templates'

#the function to handle any requests sent to the home page
@app.route('/', methods = ['GET', 'POST'])
def WEB_INDEX():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):
        
        #variable for the list of proxies
        listOfProxies = []

        #connect to the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get the list of proxies from the database
        listOfProxiesFromDB = DATABASE_CURSOR.execute('SELECT proxy_url FROM proxies').fetchall()

        #iterate through the proxies and turn them into the list of proxies that the template loader can use
        for proxy in listOfProxiesFromDB:

            #add it to the list of proxies
            listOfProxies.append(proxy[0])

        #return the home page
        return flask.render_template('index.html', applicationName = GET_APP_TITLE(), username = flask.session['LOGGED_IN_ACCOUNT_DATA'][0], downloadDirs = GET_DL_DIRS(), DEFAULT_VIDEO_DOWNLOAD_DIR = DEFAULT_VIDEO_DOWNLOAD_DIR, proxies = listOfProxies)
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = GET_APP_TITLE()) 

#the function to handle any requests sent to the queue page this is where it triggers the server to download the media
@app.route('/queue', methods = ['POST'])
def WEB_QUEUE():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #make a temporary variable for the valid video formats which can be non-destructively edited
        tmpValidVideoFormats = validVideoFormats

        #get the form data
        YTDL_URL = str(flask.request.form.get('url'))
        YTDL_FORMAT = str(flask.request.form.get('format'))
        YTDL_DIR = str(flask.request.form.get('directory'))
        YTDL_ORDER = str(flask.request.form.get('order'))
        YTDL_PROXY = str(flask.request.form.get('proxy'))
        YTDL_FOVERRIDE = str(flask.request.form.get('custom_format'))
        YTDL_RMDATE = 0 if str(flask.request.form.get('remove_date')) == 'None' else 1
        print(YTDL_RMDATE)

        #check if there is a custom format
        if (YTDL_FOVERRIDE != ''):

            #set the format as the overridden format
            YTDL_FORMAT = YTDL_FOVERRIDE

            #add the format to the tmp valid video format variable
            tmpValidVideoFormats.append(YTDL_FORMAT)

        #check if the directory is in the download-dir.txt list or is the default directory
        if (YTDL_DIR not in [*GET_DL_DIRS(), DEFAULT_VIDEO_DOWNLOAD_DIR, '#browser2computer']):
            
            #since the directory was not in the list of valid directories, return an error
            return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'The directory was not in the list of valid directories.')
        
        #check that the video format is valid
        if (YTDL_FORMAT.lower() not in [*tmpValidVideoFormats]):

            #the format is incorrect, dont download and return an error
            return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'The download format selected was incorrect for this type of media. Try using bestvideo or bestaudio if you are unsure which one works.')

        #the list of youtube videos to be downloaded (normally one one, but can be multiple in the case of a playlist)
        youtubeDLVideoList = []

        #get the video data
        try:

            #check if there is a proxy to be used
            if (YTDL_PROXY == '#none'):

                #no proxy, download normally
                youtubeDLObject = youtube_dl.YoutubeDL({'default_search':'youtube'})
            
            #there is a proxy
            else:

                #use the proxy to download it
                youtubeDLObject = youtube_dl.YoutubeDL({'default_search':'youtube', 'proxy':YTDL_PROXY})

            #get the video data for the playlist/channel/video
            videoData = youtubeDLObject.extract_info(YTDL_URL, download = False)
            
            #check if it is a playlist by checking if the 'entries' key exists
            if ('entries' in videoData):

                #add all the videos to the list
                for video in videoData['entries']:
                    youtubeDLVideoList.append([video['webpage_url'], video['title']]) #[url, title]
            
            #it is a video and not a playlist
            else:

                #add the video to the list
                youtubeDLVideoList.append([videoData['webpage_url'], videoData['title']]) #[url, title]
                
        #the url probably wasnt supported
        except:

            #redirect the user to the error page
            return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'General error downloading the video. This site/format is probably not supported. Try using bestvideo/bestaudio if you are sure that this site is supported.')

        #the database connection
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')

        #the database cursor
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #if the video order is random then shuffle the video list
        if (YTDL_ORDER == 'random'):
            
            #shuffle the order of the videos randomly
            random.shuffle(youtubeDLVideoList)

        #add the videos to the database history
        for video in youtubeDLVideoList:
            DATABASE_CURSOR.execute(
                'INSERT INTO download_history (url, title, status, timestamp, format, download_folder_path, actual_download_folder_path, proxy, rm_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                (video[0], video[1], 1, datetime.datetime.timestamp(datetime.datetime.now()), YTDL_FORMAT, YTDL_DIR, YTDL_DIR if YTDL_DIR != '#browser2computer' else DEFAULT_VIDEO_DOWNLOAD_DIR, YTDL_PROXY, YTDL_RMDATE)
            )
            YTDL_DL_ID = DATABASE_CURSOR.lastrowid #the id of the download, in the database
            DATABASE_CONNECTION.commit()

            #if the directory is set to the browser to computer download, assume that its a singular video, and download it (this will run only once, since it returns something no matter what)
            if (YTDL_DIR == '#browser2computer'):

                #set the directory to the default download dir
                YTDL_DIR = DEFAULT_VIDEO_DOWNLOAD_DIR

                #put this inside a try catch statement for simple error handling
                try:

                    #updat the database and tell it that the download is happening now
                    DATABASE_CONNECTION.execute('UPDATE download_history SET status = ? WHERE download_id = ?', ('2', YTDL_DL_ID))
                    DATABASE_CONNECTION.commit()

                    #the path for the file that is being downloaded
                    downloadedVideoFilePath = downloadVideo(video[0], YTDL_FORMAT, parentDownloadDir = YTDL_DIR)

                    #update the database and tell it that the download was successful
                    DATABASE_CONNECTION.execute('UPDATE download_history SET status = ? WHERE download_id = ?', ('3', YTDL_DL_ID))
                    DATABASE_CONNECTION.commit()

                    #download the video to the browser
                    return flask.send_file(downloadedVideoFilePath, as_attachment = True)

                #something went wrong, it was probably the wrong link
                except IOError:

                    #return the error page
                    return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'Something went wrong while your video was being prepared.')

                    #update the database and tell it that the download was unsuccessful
                    DATABASE_CONNECTION.execute('UPDATE download_history SET status = ? WHERE download_id = ?', ('4', video[3]))
                    DATABASE_CONNECTION.commit()

        #close the database connection
        DATABASE_CONNECTION.close()

        #return the queue page
        return flask.render_template('queue.html', applicationName = GET_APP_TITLE(), username = flask.session['LOGGED_IN_ACCOUNT_DATA'][0], vidURL = YTDL_URL, vidQualSet = YTDL_FORMAT)
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = GET_APP_TITLE())

#the function to handle any requests to the download history page
@app.route('/history', methods = ['GET', 'POST'])
def WEB_HISTORY():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):
        
        #all of this code has been (temporarily) phased out with the new client side api requests being the new method 
        #this code is still being kept in case somebody would prefer to mod their installation to not use the api and generate the webpage server side
        #this code can also be repurposed with an option to refresh the webpage or have it only load once
        '''
        #the database connection
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get the history data
        DATABASE_CURSOR.execute('SELECT * FROM download_history ORDER BY download_id DESC LIMIT 200')
        databaseRows = DATABASE_CURSOR.fetchall()

        #the parsed data
        databaseRowsParsed = []

        #iterate through the rows and make them user friendly
        for rows in databaseRows:

            databaseRowsParsed.append([
                rows[0], #id
                rows[1], #title
                rows[2], #url
                DOWNLOAD_STATUSES[rows[3]], #status
                datetime.datetime.fromtimestamp(rows[4]).strftime('%m/%d/%Y - %H:%M:%S'), #timestamp
                rows[5], #format
                rows[6], #download dir path
                DOWNLOAD_STATUS_COLOR_CLASSES[rows[3]] #download color
            ])
        '''

        #return the history page
        return flask.render_template('history.html', applicationName = GET_APP_TITLE(), username = flask.session['LOGGED_IN_ACCOUNT_DATA'][0])
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = GET_APP_TITLE())

#the function to handle requests to the history pages api (for auto refreshing the page) (allow both get and post, but post is preferred)
@app.route('/history/.json', methods = ['GET', 'POST'])
def WEB_HISTORY_JSON():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #connect to the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get the data about the download history
        DATABASE_CURSOR.execute('SELECT * FROM download_history ORDER BY download_id DESC LIMIT 200')
        databaseRows = DATABASE_CURSOR.fetchall()        
        
        #return the data so that the page can refresh
        return {
            'rows':databaseRows
        }
    
    #the user isnt logged in
    else:

        #return an error (return 403 forbidden error because they shouldnt be able to access it)
        return {'error':'You are not logged in.'}, 403

#the function to handle any requests to the history clear page
@app.route('/historyclr', methods = ['POST'])
def WEB_HISTORYCLR():
    
    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):
        
        #check that they are an admin

        #connect to the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get the data for the current user to make sure that they are an admin
        DATABASE_CURSOR.execute('SELECT admin FROM users WHERE username = ?', (flask.session['LOGGED_IN_ACCOUNT_DATA'][0],))
        adminPrivelegeResults = DATABASE_CURSOR.fetchall()[0][0]
        
        #check that their privelege is 1 and not 0 (means they are an admin)
        if (str(adminPrivelegeResults) == '1'):

            #delete all the history table rows
            DATABASE_CONNECTION.execute('DELETE FROM download_history')
            DATABASE_CONNECTION.commit()
            
            #redirect the user to the admin page
            return flask.redirect(flask.url_for('WEB_ADMIN'))

        #they arent an admin
        else:

            #return an error
            return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'You do not have permission to clear the history.')
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = GET_APP_TITLE())

#the function to handle any requests to the login page
@app.route('/login', methods = ['GET', 'POST'])
def WEB_LOGIN():

    #return the login page
    return flask.render_template('login.html', applicationName = GET_APP_TITLE())

#the function to handle any requests to the logout page
@app.route('/logout', methods = ['GET', 'POST'])
def WEB_LOGOUT():

    #try to remove the session variables
    try:

        #remove the users session variables
        del flask.session['LOGGED_IN_ACCOUNT_DATA']
    
    #something went wrong, they probably werent even logged in
    except:
        pass

    #redirect the user to the home page
    return flask.redirect(flask.url_for('WEB_INDEX'))

#the function to handle any requests to the authentication page (for logging in, not for signing up)
@app.route('/auth', methods = ['POST'])
def WEB_AUTH():

    #the page that sent the post request to authenticate
    referringURL = flask.request.referrer

    #get the path in the referring url (will return something like ['', 'login', '']) so you still need to remove the empty strings
    referringURLPath = (URLLIB_PARSE.urlparse(referringURL).path).split('/')

    #remove the empty strings in the url path list
    for i in range(referringURLPath.count('')):

        #remove an empty string
        referringURLPath.remove('')
    
    #the path thats now parsed so that itll always be the same
    alwaysSamePath = '/'.join(referringURLPath)
    
    #initialize a connection with the database
    DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')

    #giant try catch just in case
    try:
    
        #get the login form data
        LOGIN_FORM_USERNAME = str(flask.request.form.get('username'))
        LOGIN_FORM_PASSWORD = str(flask.request.form.get('password'))

        #get the hashed password for the username (if the length of the response is 0, there is no user that exists with that name, so give an error)
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()
        DATABASE_CURSOR.execute('SELECT password FROM users WHERE username = ?', (LOGIN_FORM_USERNAME,)) #this tuple has to have a , at the end because of this error https://stackoverflow.com/questions/16856647/sqlite3-programmingerror-incorrect-number-of-bindings-supplied-the-current-sta
        databaseResults = DATABASE_CURSOR.fetchall()
        if (len(databaseResults) == 0):

            #return an at the webpage
            print('Failed login for {}'.format(LOGIN_FORM_USERNAME))
            return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'Invalid username or password. Login failed.')
        
        #match the two passwords
        DATABASE_PASSWORD_HASH = databaseResults[0][0]
        if (not WZS.check_password_hash(DATABASE_PASSWORD_HASH, LOGIN_FORM_PASSWORD)):

            #the passwords didnt match, return an error at the webpage
            print('Failed login for {}'.format(LOGIN_FORM_USERNAME))
            return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'Invalid username or password. Login failed.')
                    
        #set up the session data [username, password]
        flask.session['LOGGED_IN_ACCOUNT_DATA'] = [LOGIN_FORM_USERNAME, LOGIN_FORM_PASSWORD]
    
    #something went wrong, notify the user
    except:
        
        #return an error at the webpage
        print('Failed login for {}'.format(LOGIN_FORM_USERNAME))
        return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'Invalid username or password. Login failed.')
    
    #return the temprary page
    return flask.redirect(flask.url_for('WEB_INDEX'))

#the function to handle any requests to the add user page (only accessible by post request, by admins only)
@app.route('/adduser', methods = ['POST'])
def WEB_ADDUSER():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #connect to the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get the data for the current user to make sure that they are an admin
        DATABASE_CURSOR.execute('SELECT admin FROM users WHERE username = ?', (flask.session['LOGGED_IN_ACCOUNT_DATA'][0],))
        adminPrivelegeResults = DATABASE_CURSOR.fetchall()[0][0]

        #check that their privelege is 1 and not 0
        if (str(adminPrivelegeResults) == '1'):

            #get the new user data
            NEW_USER_USERNAME = str(flask.request.form.get('new_username'))
            NEW_USER_PASSWORD = str(flask.request.form.get('new_password'))
            NEW_USER_PASSWORD_CONFIRM = str(flask.request.form.get('new_password_confirm'))

            #check that the passwords match
            if (NEW_USER_PASSWORD != NEW_USER_PASSWORD_CONFIRM):

                #return an error that says the passwords dont match
                return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'New user passwords didn\'t match.')

            #check that the username isnt blank
            if (NEW_USER_USERNAME.isspace() or NEW_USER_USERNAME == ''):

                #return an error page that says the username cant be blank
                return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'Users cant have a blank username.')
            
            #hash the users password
            NEW_USER_PASSWORD = WZS.generate_password_hash(NEW_USER_PASSWORD)

            #add the user to the database
            DATABASE_CONNECTION.execute('INSERT INTO users (username, password, admin) VALUES (?, ?, ?)', (NEW_USER_USERNAME, NEW_USER_PASSWORD, 0))
            DATABASE_CONNECTION.commit()

            #return the the admin page so they can continue
            return flask.redirect(flask.url_for('WEB_ADMIN'))
        
        #they arent an admin
        else:

            #return the home page
            return flask.redirect(flask.url_for('WEB_INDEX'))

    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = GET_APP_TITLE())

#the function to handle any requests to the delete user page (only accessible by post request, by admins only)
@app.route('/deleteuser', methods = ['POST'])
def WEB_DELETEUSER():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #connect to the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get the data for the current user to make sure that they are an admin
        DATABASE_CURSOR.execute('SELECT admin FROM users WHERE username = ?', (flask.session['LOGGED_IN_ACCOUNT_DATA'][0],))
        adminPrivelegeResults = DATABASE_CURSOR.fetchall()[0][0]

        #check that their privelege is 1 and not 0
        if (str(adminPrivelegeResults) == '1'):

            #get the username of the (soon to be) deleted user
            user = str(flask.request.form.get('username'))

            #get whether or not the user they are trying to delete is an admin, admins cant be deleted via the web interface
            DATABASE_CURSOR.execute('SELECT admin FROM users WHERE username = ?', (user,))
            adminPrivelegeResults = DATABASE_CURSOR.fetchall()[0][0]

            #if the user they are trying to delete is an admin, return an error
            if (str(adminPrivelegeResults) == '1'):

                #return the error page
                return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'User delete failed. Can\'t delete admins via the web interface.')
            
            #delete the user
            DATABASE_CONNECTION.execute('DELETE FROM users WHERE username = ?', (user,))
            DATABASE_CONNECTION.commit()

            #return the the admin page so they can continue
            return flask.redirect(flask.url_for('WEB_ADMIN'))
        
        #they arent an admin
        else:

            #return the home page
            return flask.redirect(flask.url_for('WEB_INDEX'))

    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = GET_APP_TITLE())

#the function to generate a registration key
@app.route('/addregkey', methods = ['POST'])
def WEB_MAKEREGKEY():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #connect to the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get the data for the current user to make sure that they are an admin
        DATABASE_CURSOR.execute('SELECT admin FROM users WHERE username = ?', (flask.session['LOGGED_IN_ACCOUNT_DATA'][0],))
        adminPrivelegeResults = DATABASE_CURSOR.fetchall()[0][0]

        #check that their privelege is 1 and not 0
        if (str(adminPrivelegeResults) == '1'):

            #make the new registration key
            #i know sha256 is bad, but it doesnt matter here, this is just a randomly generated key for creating a user account, and it just has to be individual, which is what you get by sha256-ing a random integer
            #if you see an issue with this, then raise an issue on the github repo, id be happy to fix this if it is a security concern
            newRandomRegistrationKey = str(hashlib.sha256(str(random.randint(0, 1000000)).encode()).hexdigest())

            #add the key to the database
            DATABASE_CONNECTION.execute('INSERT INTO app_config (config_data_title, config_data_content) VALUES (?, ?)', ('REGISTRATION_KEY', newRandomRegistrationKey))
            DATABASE_CONNECTION.commit()

            #return the user to the admin page
            return flask.redirect(flask.url_for('WEB_ADMIN'))
        
        #they arent an admin
        else:

            #return the home page
            return flask.redirect(flask.url_for('WEB_INDEX'))

    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = GET_APP_TITLE())

#the function to delete registration keys
@app.route('/delregkey', methods = ['POST'])
def WEB_DELETEREGKEY():
    
    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #connect to the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get the data for the current user to make sure that they are an admin
        DATABASE_CURSOR.execute('SELECT admin FROM users WHERE username = ?', (flask.session['LOGGED_IN_ACCOUNT_DATA'][0],))
        adminPrivelegeResults = DATABASE_CURSOR.fetchall()[0][0]

        #check that their privelege is 1 and not 0
        if (str(adminPrivelegeResults) == '1'):

            #get the id of the key that is going to be deleted
            keyID = flask.request.form.get('key_id')
            
            #delete the key
            DATABASE_CONNECTION.execute('DELETE FROM app_config WHERE config_data_id = ?', (keyID,))
            DATABASE_CONNECTION.commit()

            #return the user to the admin page
            return flask.redirect(flask.url_for('WEB_ADMIN'))
        
        #they arent an admin
        else:

            #return the home page
            return flask.redirect(flask.url_for('WEB_INDEX'))

    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = GET_APP_TITLE())

#the function to handle any requests to the subscriptions page
@app.route('/subscriptions', methods = ['GET', 'POST'])
def WEB_SUBSCRIPTIONS():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        
        #get the subscription data from the database (lines below)

        #connect to the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get all the data from the subscriptions table (its fine to dump it all, no sensitive data is here)
        DATABASE_CURSOR.execute('SELECT * FROM subscriptions ORDER BY subscription_id DESC') #order by descending so that the most recent ones come first
        databaseSubscriptionsDump = DATABASE_CURSOR.fetchall()

        #return the subscriptions page
        return flask.render_template('subscriptions.html', applicationName = GET_APP_TITLE(), username = flask.session['LOGGED_IN_ACCOUNT_DATA'][0], downloadDirs = GET_DL_DIRS(get_default = True), subscriptions = databaseSubscriptionsDump)
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = GET_APP_TITLE())

#the function to handle any requests to the subscription manager page
@app.route('/managesubscription', methods = ['POST'])
def WEB_MANAGESUBSCRIPTION():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #get the type of action that is happening
        ACTION_TYPE = str(flask.request.form.get('action'))

        #if the action type is "add" then the user is trying to add a subscription
        if (ACTION_TYPE == 'add'):

            #get the form data
            FORM_URL = str(flask.request.form.get('url'))
            FORM_FORMAT = str(flask.request.form.get('format'))
            FORM_WHAT2DL = str(flask.request.form.get('what_videos_to_download')) #what2dl = what to download
            FORM_DOWNLOADDIR = str(flask.request.form.get('dir'))

            #try to get the list of videos
            try:

                #get the list of videos
                youtubeDLObject = youtube_dl.YoutubeDL({'default_search':'youtube'})
                playlistOrChannelData = youtubeDLObject.extract_info(FORM_URL, download = False)

                #check if it is a playlist/channel
                if ('entries' in playlistOrChannelData):

                    #add the subscription to the subscription table (the code below)

                    #create the database connection
                    DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
                    DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

                    #the list of "downloaded" videos
                    downloadedVideos = []

                    #if the user only wants the new videos to be downloaded then get a list of the past videos
                    if (FORM_WHAT2DL == 'new'):
                        for video in playlistOrChannelData['entries']:

                            #add the webpage url
                            downloadedVideos.append(video['webpage_url'])

                    #insert the data to the database
                    DATABASE_CURSOR.execute(
                        'INSERT INTO subscriptions (video_list_url, format, download_dir, downloaded_video_list_json) VALUES (?, ?, ?, ?)',
                        (FORM_URL, FORM_FORMAT, FORM_DOWNLOADDIR, json.dumps(downloadedVideos))
                    )
                    DATABASE_CONNECTION.commit()

                    #return the user back to the subscriptions page
                    return flask.redirect(flask.url_for('WEB_SUBSCRIPTIONS'))

                #it isnt a playlist/channel
                else:
                    
                    #return an error
                    return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'The link you tried to subscribe to was not a playlist or channel.')
            
            #the was not from a supported url
            except:

                #return the error page
                return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'The link you tried to use was not from a supported website.')
        
        #check if the action is a delete action
        elif (ACTION_TYPE == 'delete'):

            #get the form data
            FORM_ID = str(flask.request.form.get('subscription_id'))

            #delete the entry with the matching id in the subscriptions table
            DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
            DATABASE_CONNECTION.execute('DELETE FROM subscriptions WHERE subscription_id = ?', (FORM_ID,))
            DATABASE_CONNECTION.commit()

            #return the user to the subscriptions page
            return flask.redirect(flask.url_for('WEB_SUBSCRIPTIONS'))

        #the action type is unknown
        else:

            #return the error page
            return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'Unknown action type: "{}".'.format(ACTION_TYPE))

    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = GET_APP_TITLE())

#the function to handle any requests to the administrator page
@app.route('/admin', methods = ['GET', 'POST'])
def WEB_ADMIN():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #connect to the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get the data for the current user to make sure that they are an admin
        DATABASE_CURSOR.execute('SELECT admin FROM users WHERE username = ?', (flask.session['LOGGED_IN_ACCOUNT_DATA'][0],))
        adminPrivelegeResults = DATABASE_CURSOR.fetchall()[0][0]

        #get the data for the registration keys
        DATABASE_CURSOR.execute('SELECT config_data_content, config_data_id FROM app_config WHERE config_data_title = ?', ('REGISTRATION_KEY',))
        registrationKeys = DATABASE_CURSOR.fetchall()
        
        #check that their privelege is 1 and not 0
        if (str(adminPrivelegeResults) == '1'):

            #get the data for the users
            DATABASE_CURSOR.execute('SELECT * FROM users')
            userData = DATABASE_CURSOR.fetchall()
            
            #the user data that is going to be sent to the browser
            userDataForBrowser = []

            #iterate through the users and add the "removable" variable
            for user in userData:

                #the line of data that is being added
                userDataLine = [
                    user[0], #username
                    False, #is an admin
                ]
                
                #check if the user is an admin
                if (str(user[2]) == '1'):
                    
                    userDataLine[1] = True
                
                #append the user data to the user data for browser list
                userDataForBrowser.append(userDataLine)
            
            #get a list of the proxies
            proxies = DATABASE_CURSOR.execute('SELECT * FROM proxies').fetchall()

            #return the admin page
            return flask.render_template('admin.html', applicationName = GET_APP_TITLE(), userData = userDataForBrowser, username = flask.session['LOGGED_IN_ACCOUNT_DATA'][0], downloadDirs = GET_DL_DIRS(), proxies = proxies, defaultDownloadDir = DEFAULT_VIDEO_DOWNLOAD_DIR, registerKeys = registrationKeys)
        
        #they dont have admin priveleges, just return them to the homepage
        else:

            #return the return the home page page
            return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'You aren\'t an administrator, so you can\'t access this page. Please speak to your system administrator.')
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = GET_APP_TITLE())

#function to handle requests to the admin action page
@app.route('/adminaction', methods = ['POST'])
def WEB_ADMINACTION():

    #import the global download dir variable since it will be changed
    global DEFAULT_VIDEO_DOWNLOAD_DIR

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #connect to the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get the form data
        ACTION_TYPE = str(flask.request.form.get('action_type'))

        #if the action type is the same for upadting the default download directory
        if (ACTION_TYPE == 'add_default_download_dir'):

            #get the new default download dir
            newDefaultDLDir = str(flask.request.form.get('default_download_dir'))

            #check that the directory exists
            if (not os.path.exists(newDefaultDLDir)):
                
                #the directory doesnt exist, return an error
                return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'The directory you tried to set as the new default download directory does not exist.')
            
            #set the new default download directory
            DEFAULT_VIDEO_DOWNLOAD_DIR = newDefaultDLDir
            DATABASE_CONNECTION.execute('UPDATE app_config SET config_data_content = ? WHERE config_data_title = ?', (newDefaultDLDir, 'DEFAULT_DOWNLOAD_DIR'))
            DATABASE_CONNECTION.commit()
        
        #if the action type is the same for adding a download directory
        if (ACTION_TYPE == 'add_alt_download_dir'):

            #get the new directory
            newDLDir = str(flask.request.form.get('new_download_dir'))

            #check if the directory exists
            if (not os.path.exists(newDLDir)):

                #the directory doesnt exist, reutrn an error
                return flask.render_template('error2.html', applicationName = GET_APP_TITLE(), error = 'The directory you tried to add does not exist.')
            
            #add the new download directory
            DATABASE_CONNECTION.execute('INSERT INTO download_directories (dir_path) VALUES (?)', (newDLDir,))
            DATABASE_CONNECTION.commit()
        
        #if the action type is the same for deleting a directory
        if (ACTION_TYPE == 'delete'):

            #get the directory to delete
            directoryToDelete = str(flask.request.form.get('download_dir_path'))

            #delete all occurences of the directory (just in case more than one has been added)
            DATABASE_CONNECTION.execute('DELETE FROM download_directories WHERE dir_path = ?', (directoryToDelete,))
            DATABASE_CONNECTION.commit()
        
        #if the action type is adding a proxy
        if (ACTION_TYPE == 'add_proxy_conn'):

            #get the proxy address
            proxyAddress = str(flask.request.form.get('proxy_addr'))

            #add the proxy to the database
            DATABASE_CONNECTION.execute('INSERT INTO proxies (proxy_url) VALUES (?)', (proxyAddress,))
            DATABASE_CONNECTION.commit()
        
        #if the action type is deleting a proxy
        if (ACTION_TYPE == 'delete_proxy'):

            #get the id of the proxy
            proxyID = str(flask.request.form.get('proxy_row_id'))

            #delete the proxy entry
            DATABASE_CONNECTION.execute('DELETE FROM proxies WHERE proxy_id = ?', (proxyID,))
            DATABASE_CONNECTION.commit()
        
        #if the action type is updating the app title
        if (ACTION_TYPE == 'edit_server_title'):

            #get the new title
            newServerTitle = str(flask.request.form.get('new_server_title'))

            #update the server title in the database
            DATABASE_CONNECTION.execute('UPDATE app_config SET config_data_content = ? WHERE config_data_title = ?', (newServerTitle, 'APP_TITLE'))
            DATABASE_CONNECTION.commit()

        #redirect the user back to the admin page
        return flask.redirect(flask.url_for('WEB_ADMIN'))
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = GET_APP_TITLE())

#function to check whether or not the user is logged in (userSession should be the flask.session['LOGGED_IN_ACCOUNT_DATA'] variable)
def isUserLoggedIn(userSession) -> bool:

    #massive try catch for this, if theres an error, assume they arent logged in
    try:

        #the user credentials
        USERNAME = userSession['LOGGED_IN_ACCOUNT_DATA'][0]
        PASSWORD = userSession['LOGGED_IN_ACCOUNT_DATA'][1]

        #connect to the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #try to get the users password that is in the database
        passwordGetResults = DATABASE_CURSOR.execute('SELECT password FROM users WHERE username = ?', (USERNAME,)) #this tuple has to have a , at the end because of this error https://stackoverflow.com/questions/16856647/sqlite3-programmingerror-incorrect-number-of-bindings-supplied-the-current-sta

        #check if the passwords match
        if (not WZS.check_password_hash(passwordGetResults.fetchall()[0][0], PASSWORD)):

            #return false since they dont match
            return False
        
        #the passwords match, so return true
        return True

    #something went wrong, guess they arent logged in
    except:

        #return false (they werent logged in)
        return False

#function to download videos (returns the path of the downloaded video)
def downloadVideo(videoURL, videoFormat, parentDownloadDir = DEFAULT_VIDEO_DOWNLOAD_DIR, proxy = '#none', rmDate = 0) -> str:

    #check that the video download directory exists
    if (not os.path.exists(DEFAULT_VIDEO_DOWNLOAD_DIR)):

        #since the directory doesnt exist, make it
        os.mkdir(DEFAULT_VIDEO_DOWNLOAD_DIR)

    #the youtube-dl temporary file name (just make it a timestamp so that it doesnt overwrite anything)
    tmpFileNameNumber = str(time.time())
    tmpFileNameNumberOriginal = tmpFileNameNumber

    #check if the format is ultra
    if (videoFormat == 'ultra'):

        #set the video format as a custom format to get maximum quality
        videoFormat = 'bestvideo[height>2160]+140/(bestvideo[height=2160][fps>30]+251)/bestvideo[height=2160]+251/bestvideo[height=2160]+140/(bestvideo[height=1440][fps>30]+251)/bestvideo[height=1440]+251/bestvideo[height=1440]+140/(bestvideo[height=1080][fps>30]+251)/bestvideo[height=1080]+251/bestvideo[height=1080]+140/(bestvideo[height=720][fps>30]+251)/bestvideo+251/bestvideo+140/best'

    #the arguments for the downloader
    ytdlArgs = {
        'outtmpl':'{}/{}.%(ext)s'.format(parentDownloadDir, tmpFileNameNumber),
        'default_search':'youtube',
        'proxy':proxy,
        'format':videoFormat
    }

    #check if there is a proxy being used
    if (proxy == '#none'):

        #set up the youtube downloader object without a proxy (remove the proxy key)
        del ytdlArgs['proxy']
    
    #check if the format is best (no format at all)
    if (videoFormat == 'best'):

        #remove the format key (it downloads the best format automatically)
        del ytdlArgs['format']
        
    #the youtube downloader object
    youtubeDLObject = youtube_dl.YoutubeDL(ytdlArgs)

    #download the metadata so that the video can be tagged for usage with streaming servers
    youtubeVideoData = youtubeDLObject.extract_info(videoURL, download = False)
    
    #the status on the attempt to get the video metadata
    videoDataMetadataGetStatus = True

    #add the extension onto the temporary file name so that it can be referrenced by the program later
    tmpFileNameNumber = str(tmpFileNameNumber) + '.' + youtubeVideoData['ext']

    #try to get the video metadata (seems to mostly only work for youtube)
    try:

        #try to get the metadata from the video that will be used for tagging (if this fails to happen, then it will fall back to the default plain file name)
        testVideoData = {
            'ext':youtubeVideoData['ext'],
            'title':youtubeVideoData['title'],
            'uploader':youtubeVideoData['uploader'],
            'id':youtubeVideoData['id'],
            'playlist':youtubeVideoData['album'],
            'playlist_index':youtubeVideoData['playlist_index'],
            'upload_year':str(youtubeVideoData['upload_date'])[0:4],
            'upload_month':str(youtubeVideoData['upload_date'])[4:6],
            'upload_day':str(youtubeVideoData['upload_date'])[6:8]
        }

        #the output file name
        outputFileName = '{}{}{}{}.{}'.format(
            str(testVideoData['upload_year']) + '_' if int(rmDate) == 0 else '', #upload year 
            str(testVideoData['upload_month']) + '_' if int(rmDate) == 0 else '', #upload month
            str(testVideoData['upload_day']) + '_' if int(rmDate) == 0 else '', #upload day
            testVideoData['title'], #title
            testVideoData['ext'] #extension
        )

    #there was an error getting the metadata for the video (probably not a youtube link)
    except:

        #print a warning to the console
        print('Error downloading {} with youtube metadata, using default filename instead.'.format(videoURL))

        #set the get status to false (failure)
        videoDataMetadataGetStatus = False

        #the output file name (without the fancy youtube metadata)
        outputFileName = '{}.{}'.format(
            youtubeVideoData['title'], #title
            youtubeVideoData['ext'] #extension
        )

    #download the video
    youtubeDLObject.download([videoURL])

    #check if the original video exists or if the video was merged into something else
    if (tmpFileNameNumber not in os.listdir(parentDownloadDir)):

        #alert the user that the original video was not found and that the program will attempt to find a similar video
        print('Original video not found for {}. Will try to find the new merged file.'.format(tmpFileNameNumber))

        #search the directory for a similar file
        for file in os.listdir(parentDownloadDir):

            #check if the file has the same timestamp on it
            if (tmpFileNameNumberOriginal in file):

                #tell the program that a likely match was found (in the end this isnt the best system, but chances are that itll find the right match)
                print('Likely match for {} was found: {}.'.format(tmpFileNameNumber, file))
                
                #set the tmp file name as the match
                tmpFileNameNumber = file

                #break out of the for loop
                break

    #only encode the metadata if the get status is good
    if (videoDataMetadataGetStatus):

        #encode the media file with the data
        os.system('ffmpeg -i "{}/{}" -strict -2 -metadata title="{}" -metadata author="{}" -metadata artist="{}" -c copy -c:a aac "{}/{}" -nostdin -y'.format(
            parentDownloadDir, #download directory
            tmpFileNameNumber, #filename
            youtubeVideoData['title'], #metadata title
            youtubeVideoData['uploader'], #metadata author (for video)
            youtubeVideoData['uploader'], #metadata artist (for music)
            parentDownloadDir, #download directory
            outputFileName #the name of the output file
        ))

        #remove the original file
        os.remove('{}/{}'.format(parentDownloadDir, tmpFileNameNumber))
    
    #otherwise just rename the file
    else:

        #move/rename it
        shutil.move('{}/{}'.format(parentDownloadDir, tmpFileNameNumber), '{}/{}'.format(parentDownloadDir, outputFileName))

    #return the path of the video
    return '{}/{}'.format(parentDownloadDir, outputFileName)

#function to get the app's title (advantage of this to the older method is that the app title can be updated without a restart)
def GET_APP_TITLE() -> str:

    #connect to the database
    DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
    DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

    #get the app title
    appTitle = DATABASE_CURSOR.execute('SELECT config_data_content FROM app_config WHERE config_data_title = ?', ('APP_TITLE',)).fetchall()[0][0]

    #return the app title
    return appTitle

#function to get the download directories
def GET_DL_DIRS(get_default = False) -> list:

    #connect to the database
    DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
    DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

    #get the list of directories that can be downloaded to
    downloadDirsFromDB = DATABASE_CURSOR.execute('SELECT * FROM download_directories').fetchall()

    #the list of directories to be sent to the webpage
    downloadDirList = []

    #check if the user wants to get the default dir
    if (get_default):

        #append the default download dir to the list
        downloadDirList.append(DEFAULT_VIDEO_DOWNLOAD_DIR)

    #iterate through the database entries and validate all the entires
    for row in downloadDirsFromDB:

        #the actual path
        rowPath = row[1]

        #check if the path exists
        if (os.path.exists(rowPath)):

            #add the path to the list of download dirs now that its confirmed that it exists
            downloadDirList.append(rowPath)
    
    #return the download dirs
    return downloadDirList

#function to poll for new videos and then download them
def YTDL_POLLER():

    #loop and check for new videos every half a second
    while (1): 

        #initialize a connection with the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get the queue for the videos (the ones where the status is 1 (pending download))
        DATABASE_CURSOR.execute('SELECT download_id FROM download_history WHERE status = 1')
        pendingDownloads = DATABASE_CURSOR.fetchall()

        #check the length of the pending downloads list
        if (len(pendingDownloads) > 0):

            #update the youtube-dl package (or try to)
            try:

                #update the package using pip
                pip.main(['install', '-U', 'youtube-dl'])
            
            #it failed, just ignore it and continue without updating
            except:

                #alert the user
                print('Failed to update youtube-dl using pip.')

            #download all the videos on the queue
            for videoID in pendingDownloads:
                
                #get the first index
                videoID = videoID[0]
                
                #download the video
                try:

                    #updat the database and tell it that the download is happening now
                    DATABASE_CONNECTION.execute('UPDATE download_history SET status = ? WHERE download_id = ?', ('2', videoID))
                    DATABASE_CONNECTION.commit()

                    #videoURL, videoFormat, parentDownloadDir = DEFAULT_VIDEO_DOWNLOAD_DIR

                    #get the data about the video id
                    DATABASE_CURSOR.execute('SELECT * FROM download_history WHERE download_id = ?', (videoID,))
                    databaseRow = DATABASE_CURSOR.fetchall()[0]

                    #download the video
                    downloadPath = downloadVideo(
                        databaseRow[2], #video url
                        databaseRow[5], #video format
                        parentDownloadDir = databaseRow[7], #video download directory
                        proxy = databaseRow[8], #the proxy
                        rmDate = databaseRow[9] #the 1/0 that determines whether or not the date should be written to the filename
                    )
                    
                    #update the database and tell it that the download was successful
                    DATABASE_CONNECTION.execute('UPDATE download_history SET status = ? WHERE download_id = ?', ('3', videoID))
                    DATABASE_CONNECTION.commit()
                
                #there was an error, tell the log for now, and add a way to tell the user there was an error soon
                except:
                    print('Error downloading video id {}.'.format(videoID))

                    #update the database and tell it that the download was unsuccessful
                    DATABASE_CONNECTION.execute('UPDATE download_history SET status = ? WHERE download_id = ?', ('4', videoID))
                    DATABASE_CONNECTION.commit()

        #wait half a second
        time.sleep(0.5)

#start the poller thread
_thread.start_new_thread(YTDL_POLLER, ())