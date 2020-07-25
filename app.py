#import statements
import flask, json, requests, time, _thread, os, youtube_dl, sqlite3, datetime, flask_session, random, pip
import urllib.parse as URLLIB_PARSE
import werkzeug.security as WZS

#try to import the config file
try:
    configData = json.loads(str(open('./config.json').read()))
#the config file does not exist, tell the user to run setup.py and then exit
except FileNotFoundError:
    print('No config file was detected. Are you running in the correct directory? Did you run setup.py?')
    exit()

#the default directory for the videos to be downloaded to
DEFAULT_VIDEO_DOWNLOAD_DIR = './downloads'

#the download statuses
DOWNLOAD_STATUSES = {
    1:'Download Pending',
    2:'Downloading Now',
    3:'Downloaded',
    4:'Download Failed'
}

#the download status color classes
DOWNLOAD_STATUS_COLOR_CLASSES = {
    1:'text-warning',
    2:'text-success',
    3:'',
    4:'text-danger'
}

#the valid video formats
validVideoFormats = ['aac', 'flac', 'mp3', 'm4a', 'opus', 'vorbis', 'wav', 'bestaudio', 'mp4', 'flv', 'webm', 'ogg', 'mkv', 'avi', 'bestvideo', 'best']

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

        #variable for the list of valid download directories
        downloadDirList = []

        #get the list of lines in the download-dirs.txt file
        downloadDirListUnparsed = str(open('./download-dirs.txt').read()).split('\n')

        #iterate through the list of unparsed directories and get the valid ones
        for line in downloadDirListUnparsed:

            #just in case?
            try:

                #check that the directory is valid (doesnt start with #, isnt whitespace, and is a real directory)
                if (line[0] != '#' and not line.isspace() and line != '' and os.path.exists(line)):

                    #add the directory to the actual list
                    downloadDirList.append(line)
            
            #in case something goes wrong
            except:

                #alert that there was an error
                print('Error parsing the directory "{}".'.format(line))
        
        #variable for the list of proxies
        listOfProxies = []

        #get the list of the lines in the proxies.txt file
        listOfProxiesUnparsed = str(open('./proxies.txt').read()).split('\n')

        #iterate through the unparsed list of proxies and get rid of the invalid entries (the ones that start with pound signs)
        for proxy in listOfProxiesUnparsed:

            #check if the proxy starts with a pound sign and it isnt whitespace
            if (not proxy.isspace() and proxy != '' and proxy[0] != '#'):

                #append the proxy to the list of proxies
                listOfProxies.append(proxy)

        #return the home page
        return flask.render_template('index.html', applicationName = configData['application_name'], username = flask.session['LOGGED_IN_ACCOUNT_DATA'][0], downloadDirs = downloadDirList, DEFAULT_VIDEO_DOWNLOAD_DIR = DEFAULT_VIDEO_DOWNLOAD_DIR, proxies = listOfProxies)
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = configData['application_name']) 

#the function to handle any requests sent to the queue page this is where it triggers the server to download the media
@app.route('/queue', methods = ['POST'])
def WEB_QUEUE():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #import the global variable for the valid video formats
        global validVideoFormats

        #get the form data
        YTDL_URL = str(flask.request.form.get('url'))
        YTDL_FORMAT = str(flask.request.form.get('format'))
        YTDL_DIR = str(flask.request.form.get('directory'))
        YTDL_ORDER = str(flask.request.form.get('order'))
        YTDL_PROXY = str(flask.request.form.get('proxy'))

        #get a list of the download directories to ensure that the directory is valid
        downloadDirListUnparsed = str(open('./download-dirs.txt').read()).split('\n')

        #check if the directory is in the download-dir.txt list or is the default directory
        if (YTDL_DIR not in [*downloadDirListUnparsed, DEFAULT_VIDEO_DOWNLOAD_DIR, '#browser2computer']):
            
            #since the directory was not in the list of valid directories, return an error
            return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'The directory was not in the list of valid directories.')
        
        #check that the video format is valid
        if (YTDL_FORMAT.lower() not in validVideoFormats):

            #the format is incorrect, dont download and return an error
            return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'The download format selected was incorrect for this type of media. Try using bestvideo or bestaudio if you are unsure which one works.')

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
            return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'General error downloading the video. This site/format is probably not supported. Try using bestvideo/bestaudio if you are sure that this site is supported.')

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
                'INSERT INTO download_history (url, title, status, timestamp, format, download_folder_path, actual_download_folder_path, proxy) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
                (video[0], video[1], 1, datetime.datetime.timestamp(datetime.datetime.now()), YTDL_FORMAT, YTDL_DIR, YTDL_DIR if YTDL_DIR != '#browser2computer' else DEFAULT_VIDEO_DOWNLOAD_DIR, YTDL_PROXY)
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
                    return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'Something went wrong while your video was being prepared.')

                    #update the database and tell it that the download was unsuccessful
                    DATABASE_CONNECTION.execute('UPDATE download_history SET status = ? WHERE download_id = ?', ('4', video[3]))
                    DATABASE_CONNECTION.commit()

        #close the database connection
        DATABASE_CONNECTION.close()

        #return the queue page
        return flask.render_template('queue.html', applicationName = configData['application_name'], username = flask.session['LOGGED_IN_ACCOUNT_DATA'][0], vidURL = YTDL_URL, vidQualSet = YTDL_FORMAT)
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = configData['application_name'])

#the function to handle any requests to the download history page
@app.route('/history', methods = ['GET', 'POST'])
def WEB_HISTORY():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

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

        #return the history page
        return flask.render_template('history.html', applicationName = configData['application_name'], databaseData = databaseRowsParsed, username = flask.session['LOGGED_IN_ACCOUNT_DATA'][0])
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = configData['application_name'])

#the function to handle any requests to the login page
@app.route('/login', methods = ['GET', 'POST'])
def WEB_LOGIN():

    #return the login page
    return flask.render_template('login.html', applicationName = configData['application_name'])

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
            return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'Invalid username or password. Login failed.')
        
        #match the two passwords
        DATABASE_PASSWORD_HASH = databaseResults[0][0]
        if (not WZS.check_password_hash(DATABASE_PASSWORD_HASH, LOGIN_FORM_PASSWORD)):

            #the passwords didnt match, return an error at the webpage
            print('Failed login for {}'.format(LOGIN_FORM_USERNAME))
            return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'Invalid username or password. Login failed.')
                    
        #set up the session data [username, password]
        flask.session['LOGGED_IN_ACCOUNT_DATA'] = [LOGIN_FORM_USERNAME, LOGIN_FORM_PASSWORD]
    
    #something went wrong, notify the user
    except:
        
        #return an error at the webpage
        print('Failed login for {}'.format(LOGIN_FORM_USERNAME))
        return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'Invalid username or password. Login failed.')
    
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
                return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'New user passwords didn\'t match.')

            #check that the username isnt blank
            if (NEW_USER_USERNAME.isspace() or NEW_USER_USERNAME == ''):

                #return an error page that says the username cant be blank
                return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'Users cant have a blank username.')
            
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
        return flask.render_template('login.html', applicationName = configData['application_name'])

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
                return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'User delete failed. Can\'t delete admins via the web interface.')
            
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
        return flask.render_template('login.html', applicationName = configData['application_name'])

#the function to handle any requests to the subscriptions page
@app.route('/subscriptions', methods = ['GET', 'POST'])
def WEB_SUBSCRIPTIONS():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #variable for the list of valid download directories
        downloadDirList = [DEFAULT_VIDEO_DOWNLOAD_DIR]

        #get the list of lines in the download-dirs.txt file
        downloadDirListUnparsed = str(open('./download-dirs.txt').read()).split('\n')

        #iterate through the list of unparsed directories and get the valid ones
        for line in downloadDirListUnparsed:

            #just in case?
            try:

                #check that the directory is valid (doesnt start with #, isnt whitespace, and is a real directory)
                if (line[0] != '#' and not line.isspace() and line != '' and os.path.exists(line)):

                    #add the directory to the actual list
                    downloadDirList.append(line)
            
            #in case something goes wrong
            except:

                #alert that there was an error
                print('Error parsing the directory "{}".'.format(line))
        
        #get the subscription data from the database (lines below)

        #connect to the database
        DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
        DATABASE_CURSOR = DATABASE_CONNECTION.cursor()

        #get all the data from the subscriptions table (its fine to dump it all, no sensitive data is here)
        DATABASE_CURSOR.execute('SELECT * FROM subscriptions ORDER BY subscription_id DESC') #order by descending so that the most recent ones come first
        databaseSubscriptionsDump = DATABASE_CURSOR.fetchall()

        #return the subscriptions page
        return flask.render_template('subscriptions.html', applicationName = configData['application_name'], username = flask.session['LOGGED_IN_ACCOUNT_DATA'][0], downloadDirs = downloadDirList, subscriptions = databaseSubscriptionsDump)
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = configData['application_name'])

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
                    return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'The link you tried to subscribe to was not a playlist or channel.')
            
            #the was not from a supported url
            except:

                #return the error page
                return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'The link you tried to use was not from a supported website.')
        
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
            return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'Unknown action type: "{}".'.format(ACTION_TYPE))

    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = configData['application_name'])

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

            #return the admin page
            return flask.render_template('admin.html', applicationName = configData['application_name'], userData = userDataForBrowser, username = flask.session['LOGGED_IN_ACCOUNT_DATA'][0])
        
        #they dont have admin priveleges, just return them to the homepage
        else:

            #return the return the home page page
            return flask.render_template('error2.html', applicationName = configData['application_name'], error = 'You aren\'t an administrator, so you can\'t access this page. Please speak to your system administrator.')
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = configData['application_name'])

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
def downloadVideo(videoURL, videoFormat, parentDownloadDir = DEFAULT_VIDEO_DOWNLOAD_DIR, proxy = '#none') -> str:

    #check that the video download directory exists
    if (not os.path.exists(DEFAULT_VIDEO_DOWNLOAD_DIR)):

        #since the directory doesnt exist, make it
        os.mkdir(DEFAULT_VIDEO_DOWNLOAD_DIR)

    #the youtube-dl temporary file name (just make it a timestamp so that it doesnt overwrite anything)
    tmpFileNameNumber = str(time.time())

    #check if there is a proxy being used
    if (proxy == '#none'):

        #set up the youtube downloader object without a proxy
        youtubeDLObject = youtube_dl.YoutubeDL({'format':videoFormat,'outtmpl':'{}/{}.%(ext)s'.format(parentDownloadDir, tmpFileNameNumber),'default_search':'youtube'})
    
    #there is a proxy being used
    else:

        #set up the youtube downloader object without a proxy
        youtubeDLObject = youtube_dl.YoutubeDL({'format':videoFormat,'outtmpl':'{}/{}.%(ext)s'.format(parentDownloadDir, tmpFileNameNumber),'default_search':'youtube', 'proxy':proxy})

    #download the metadata so that the video can be tagged for usage with streaming servers
    youtubeVideoData = youtubeDLObject.extract_info(videoURL, download = False)
    
    #get the data that is needed (this isnt a nessecary step, but it makes the code easier to work with)
    youtubeVideoMetadataData = {
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

    #download the video
    youtubeDLObject.download([videoURL])

    #encode the media file with the data
    os.system('ffmpeg -i "{}/{}.{}" -metadata title="{}" -metadata author="{}" -metadata artist="{}" -c copy "{}/{}_{}_{}_{}.{}" -nostdin -y'.format(
        parentDownloadDir, #download directory
        tmpFileNameNumber, #filename
        youtubeVideoMetadataData['ext'], #extension
        youtubeVideoMetadataData['title'], #metadata title
        youtubeVideoMetadataData['uploader'], #metadata author (for video)
        youtubeVideoMetadataData['uploader'], #metadata artist (for music)
        parentDownloadDir, #download directory
        youtubeVideoMetadataData['upload_year'], #upload year 
        youtubeVideoMetadataData['upload_month'], #upload month
        youtubeVideoMetadataData['upload_day'], #upload day
        youtubeVideoMetadataData['title'], #title
        youtubeVideoMetadataData['ext'] #extension
    ))

    #delete the original file
    os.remove('{}/{}.{}'.format(parentDownloadDir, tmpFileNameNumber, youtubeVideoMetadataData['ext']))

    #return the path of the video
    return '{}/{}_{}_{}_{}.{}'.format(parentDownloadDir, youtubeVideoMetadataData['upload_year'], youtubeVideoMetadataData['upload_month'], youtubeVideoMetadataData['upload_day'], youtubeVideoMetadataData['title'], youtubeVideoMetadataData['ext'])

#def downloadVideo(videoURL, videoFormat, videoID, parentDownloadDir = DEFAULT_VIDEO_DOWNLOAD_DIR) -> str:

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

                    print(databaseRow)

                    #download the video
                    downloadPath = downloadVideo(
                        databaseRow[2], #video url
                        databaseRow[5], #video format
                        parentDownloadDir = databaseRow[7], #video download directory
                        proxy = databaseRow[8] #the proxy
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