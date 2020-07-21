#import statements
import flask, json, requests, time, _thread, os, youtube_dl, sqlite3, datetime, flask_session, random
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

#the video queue [url, format, dir, download id]
videoQueue = []

#the valid video formats
validVideoFormats = ['aac', 'flac', 'mp3', 'm4a', 'opus', 'vorbis', 'wav', 'bestaudio', 'mp4', 'flv', 'webm', 'ogg', 'mkv', 'avi', 'bestvideo']

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
                if (line[0] != '#' and not line.isspace() and os.path.exists(line)):

                    #add the directory to the actual list
                    downloadDirList.append(line)
            
            #in case something goes wrong
            except:

                #alert that there was an error
                print('Error parsing the directory "{}".'.format(line))

        #return the home page
        return flask.render_template('index.html', applicationName = configData['application_name'], downloadDirs = downloadDirList, DEFAULT_VIDEO_DOWNLOAD_DIR = DEFAULT_VIDEO_DOWNLOAD_DIR)
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = configData['application_name']) 

#the function to handle any requests sent to the queue page this is where it triggers the server to download the media
@app.route('/queue', methods = ['GET', 'POST'])
def WEB_QUEUE():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #import the global variable for the queue and the valid video formats variable
        global videoQueue, validVideoFormats

        #get the form data
        YTDL_URL = str(flask.request.form.get('url'))
        YTDL_FORMAT = str(flask.request.form.get('format'))
        YTDL_DIR = str(flask.request.form.get('directory'))
        YTDL_ORDER = str(flask.request.form.get('order'))

        #get a list of the download directories to ensure that the directory is valid
        downloadDirListUnparsed = str(open('./download-dirs.txt').read()).split('\n')

        #check if the directory is in the download-dir.txt list or is the default directory
        if (YTDL_DIR not in [*downloadDirListUnparsed, DEFAULT_VIDEO_DOWNLOAD_DIR, '#browser2computer']):
            
            #since the directory was not in the list of valid directories, return an error
            return flask.redirect(flask.url_for('WEB_ERROR'))
        
        #check that the video format is valid
        if (YTDL_FORMAT.lower() not in validVideoFormats):

            #the format is incorrect, dont download and return an error
            return flask.redirect(flask.url_for('WEB_ERROR'))

        #the list of youtube videos to be downloaded (normally one one, but can be multiple in the case of a playlist)
        youtubeDLVideoList = []

        #get the video data
        try:
            youtubeDLObject = youtube_dl.YoutubeDL({'default_search':'youtube'})
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
            return flask.redirect(flask.url_for('WEB_ERROR'))

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
                'INSERT INTO download_history (url, title, status, timestamp, format, download_folder_path) VALUES (?, ?, ?, ?, ?, ?)', 
                (video[0], video[1], 1, datetime.datetime.timestamp(datetime.datetime.now()), YTDL_FORMAT, YTDL_DIR)
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
                    downloadedVideoFilePath = downloadVideo(video[0], YTDL_FORMAT, YTDL_DL_ID, parentDownloadDir = YTDL_DIR)

                    #update the database and tell it that the download was successful
                    DATABASE_CONNECTION.execute('UPDATE download_history SET status = ? WHERE download_id = ?', ('3', YTDL_DL_ID))
                    DATABASE_CONNECTION.commit()

                    #download the video to the browser
                    return flask.send_file(downloadedVideoFilePath, as_attachment = True)

                #something went wrong, it was probably the wrong link
                except:

                    #return the error page
                    return flask.redirect(flask.url_for('WEB_ERROR'))

                    #update the database and tell it that the download was unsuccessful
                    DATABASE_CONNECTION.execute('UPDATE download_history SET status = ? WHERE download_id = ?', ('4', video[3]))
                    DATABASE_CONNECTION.commit()

            #append the video to the queue
            videoQueue.append([video[0], YTDL_FORMAT, YTDL_DIR, YTDL_DL_ID])

        #close the database connection
        DATABASE_CONNECTION.close()

        #return the queue page
        return flask.render_template('queue.html', applicationName = configData['application_name'], vidURL = YTDL_URL, vidQualSet = YTDL_FORMAT)
    
    #the user isnt logged in
    else:
        
        #return the login page
        return flask.render_template('login.html', applicationName = configData['application_name'])

#the function to handle any requests sent to the error page (usually because a video cant be downloaded)
@app.route('/error', methods = ['GET', 'POST'])
def WEB_ERROR():

    #check that the user is logged in
    if (isUserLoggedIn(flask.session)):

        #return the error page
        return flask.render_template('error.html', applicationName = configData['application_name'])
     
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
        return flask.render_template('history.html', applicationName = configData['application_name'], databaseData = databaseRowsParsed)
    
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
            return flask.render_template('autherror.html', applicationName = configData['application_name'], error = 'Invalid username or password. Login failed.')
        
        #match the two passwords
        DATABASE_PASSWORD_HASH = databaseResults[0][0]
        if (not WZS.check_password_hash(DATABASE_PASSWORD_HASH, LOGIN_FORM_PASSWORD)):

            #the passwords didnt match, return an error at the webpage
            print('Failed login for {}'.format(LOGIN_FORM_USERNAME))
            return flask.render_template('autherror.html', applicationName = configData['application_name'], error = 'Invalid username or password. Login failed.')
                    
        #set up the session data [username, password]
        flask.session['LOGGED_IN_ACCOUNT_DATA'] = [LOGIN_FORM_USERNAME, LOGIN_FORM_PASSWORD]
    
    #something went wrong, notify the user
    except:
        
        #return an error at the webpage
        print('Failed login for {}'.format(LOGIN_FORM_USERNAME))
        return flask.render_template('autherror.html', applicationName = configData['application_name'], error = 'Invalid username or password. Login failed.')
    
    #return the temprary page
    return flask.redirect(flask.url_for('WEB_INDEX'))

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
def downloadVideo(videoURL, videoFormat, videoID, parentDownloadDir = DEFAULT_VIDEO_DOWNLOAD_DIR) -> str:

    #check that the video download directory exists
    if (not os.path.exists(DEFAULT_VIDEO_DOWNLOAD_DIR)):

        #since the directory doesnt exist, make it
        os.mkdir(DEFAULT_VIDEO_DOWNLOAD_DIR)

    #the youtube-dl temporary file name (just make it a timestamp so that it doesnt overwrite anything)
    tmpFileNameNumber = str(time.time())

    print(parentDownloadDir)

    #set up the youtube downloader object
    youtubeDLObject = youtube_dl.YoutubeDL({'format':videoFormat,'outtmpl':'{}/{}.%(ext)s'.format(parentDownloadDir, tmpFileNameNumber),'default_search':'youtube'})

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
    }

    #download the video
    youtubeDLObject.download([videoURL])

    #encode the media file with the data
    os.system('ffmpeg -i "{}/{}.{}" -metadata title="{}" -metadata author="{}" -metadata artist="{}" -c copy "{}/{}.{}" -nostdin -y'.format(
        parentDownloadDir, #download directory
        tmpFileNameNumber, #filename
        youtubeVideoMetadataData['ext'], #extension
        youtubeVideoMetadataData['title'], #metadata title
        youtubeVideoMetadataData['uploader'], #metadata author (for video)
        youtubeVideoMetadataData['uploader'], #metadata artist (for music)
        parentDownloadDir, #download directory
        youtubeVideoMetadataData['title'], #title
        youtubeVideoMetadataData['ext'] #extension
    ))

    #delete the original file
    os.remove('{}/{}.{}'.format(parentDownloadDir, tmpFileNameNumber, youtubeVideoMetadataData['ext']))

    #return the path of the video
    return '{}/{}.{}'.format(parentDownloadDir, youtubeVideoMetadataData['title'], youtubeVideoMetadataData['ext'])

#def downloadVideo(videoURL, videoFormat, videoID, parentDownloadDir = DEFAULT_VIDEO_DOWNLOAD_DIR) -> str:

#function to poll for new videos and then download them
def YTDL_POLLER():

    #import the global variable for the queue
    global videoQueue

    #loop and check for new videos every half a second
    while (1): 

        #download all the videos on the queue
        for video in videoQueue:

            #initialize a connection with the database
            DATABASE_CONNECTION = sqlite3.connect('./youtube-dl-server-database.db')
            
            #download the video
            try:

                #updat the database and tell it that the download is happening now
                DATABASE_CONNECTION.execute('UPDATE download_history SET status = ? WHERE download_id = ?', ('2', video[3]))
                DATABASE_CONNECTION.commit()

                #download the video
                downloadPath = downloadVideo(video[0], video[1], video[3], parentDownloadDir = video[2])

                #update the database and tell it that the download was successful
                DATABASE_CONNECTION.execute('UPDATE download_history SET status = ? WHERE download_id = ?', ('3', video[3]))
                DATABASE_CONNECTION.commit()
            
            #there was an error, tell the log for now, and add a way to tell the user there was an error soon
            except:
                print('Error downloading {} with quality {}.'.format(video[0], video[1]))

                #update the database and tell it that the download was unsuccessful
                DATABASE_CONNECTION.execute('UPDATE download_history SET status = ? WHERE download_id = ?', ('4', video[3]))
                DATABASE_CONNECTION.commit()
        
        #since the video queue is entirely downloaded, reset the queue
        videoQueue = []

        #wait half a second
        time.sleep(0.5)

#start the poller thread
_thread.start_new_thread(YTDL_POLLER, ())