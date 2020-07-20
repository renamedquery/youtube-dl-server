#import statements
import flask, json, requests, time, _thread, os, youtube_dl

#add authentication via google authenticator

#try to import the config file
try:
    configData = json.loads(str(open('./config.json').read()))
#the config file does not exist, tell the user to run setup.py and then exit
except FileNotFoundError:
    print('No config file was detected. Are you running in the correct directory? Did you run setup.py?')
    exit()

#the default directory for the videos to be downloaded to
DEFAULT_VIDEO_DOWNLOAD_DIR = './downloads'

#the video queue [url, format, dir]
videoQueue = []

#the valid video formats
validVideoFormats = ['aac', 'flac', 'mp3', 'm4a', 'opus', 'vorbis', 'wav', 'bestaudio', 'mp4', 'flv', 'webm', 'ogg', 'mkv', 'avi', 'bestvideo']

#create the application class
app = flask.Flask(__name__)

#set up the directory tree
app._static_folder = './static'
app.template_folder = './templates'

#the function to handle any requests sent to the home page
@app.route('/', methods = ['GET', 'POST'])
def WEB_INDEX():

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

                #add the directori to the actual list
                downloadDirList.append(line)
            
            #if the directory is invalid then warn the user
            else:
                print('There is an issue with the directory "{}" that is in your download-dirs.txt. It may not exist.'.format(line))
        
        #in case something goes wrong
        except:

            #alert that there was an error
            print('Error parsing the directori "{}".'.format(line))

    #return the home page
    return flask.render_template('index.html', applicationName = configData['application_name'], downloadDirs = downloadDirList, DEFAULT_VIDEO_DOWNLOAD_DIR = DEFAULT_VIDEO_DOWNLOAD_DIR)

#the function to handle any requests sent to the queue page (only allow POST requests) this is where it triggers the server to download the media
@app.route('/queue', methods = ['POST'])
def WEB_QUEUE():

    #import the global variable for the queue and the valid video formats variable
    global videoQueue, validVideoFormats

    #get the form data
    YTDL_URL = str(flask.request.form.get('url'))
    YTDL_FORMAT = str(flask.request.form.get('format'))
    YTDL_DIR = str(flask.request.form.get('directory'))

    #get a list of the download directories to ensure that the directory is valid
    downloadDirListUnparsed = str(open('./download-dirs.txt').read()).split('\n')

    #check if the directory is in the download-dir.txt list or is the default directory
    if (YTDL_DIR not in [*downloadDirListUnparsed, DEFAULT_VIDEO_DOWNLOAD_DIR]):
        
        #since the directory was not in the list of valid directories, return an error
        return flask.redirect(flask.url_for('WEB_ERROR'))

    #make a request to the url to check that it can be downloaded, if not return an error
    try:
        ytdlUrlRequestResponse = requests.get(url = YTDL_URL, params = {})
        if (ytdlUrlRequestResponse.status_code != 200): #status was not 200, so you probably cant download the video
            return flask.redirect(flask.url_for('WEB_ERROR'))
    #there was some sort of other error, also send them to the error page
    except:
        return flask.redirect(flask.url_for('WEB_ERROR'))
    
    #check that the video format is valid
    if (YTDL_FORMAT.lower() not in validVideoFormats):

        #the format is incorrect, dont download and return an error
        return flask.redirect(flask.url_for('WEB_ERROR'))
    
    #add the video to the queue
    videoQueue.append([YTDL_URL, YTDL_FORMAT, YTDL_DIR])

    #return the queue page
    return flask.render_template('queue.html', applicationName = configData['application_name'], vidURL = YTDL_URL, vidQualSet = YTDL_FORMAT)

#the function to handle any requests sent to the error page (usually because a video cant be downloaded)
@app.route('/error', methods = ['GET', 'POST'])
def WEB_ERROR():

    #return the error page
    return flask.render_template('error.html', applicationName = configData['application_name'])

#function to download videos
def YTDL_POLLER():

    #import the global variable for the queue
    global videoQueue

    #loop and check for new videos every half a second
    while (1): 

        #download all the videos on the queue
        for video in videoQueue:

            #check that the video download directory exists
            if (not os.path.exists(DEFAULT_VIDEO_DOWNLOAD_DIR)):

                #since the directory doesnt exist, make it
                os.mkdir(DEFAULT_VIDEO_DOWNLOAD_DIR)
            
            #download the video
            try:

                #the download directory
                downloadDir = str(video[2])

                #set up the youtube downloader object
                youtubeDLObject = youtube_dl.YoutubeDL({'format':video[1],'outtmpl':'{}/%(title)s [%(id)s].%(ext)s'.format(downloadDir),'default_search':'youtube'})

                #download the video
                youtubeDLObject.download([video[0]])

                #download the metadata so that the video can be tagged for usage with streaming servers
                youtubeVideoData = youtubeDLObject.extract_info(video[0], download = False)
                
                #get the data that is needed (this isnt a nessecary step, but it makes the code easier to work with)
                youtubeVideoMetadataData = {
                    'ext':youtubeVideoData['ext'],
                    'title':youtubeVideoData['title'],
                    'uploader':youtubeVideoData['uploader'],
                    'id':youtubeVideoData['id'],
                    'playlist':youtubeVideoData['album'],
                    'playlist_index':youtubeVideoData['playlist_index'],
                }

                #encode the media file with the data
                os.system('ffmpeg -i "{}/{} [{}].{}" -metadata title="{}" -metadata author="{}" -metadata artist="{}" -c copy "{}/{}.{}" -nostdin -y'.format(
                    downloadDir, #download directory
                    youtubeVideoMetadataData['title'], #title
                    youtubeVideoMetadataData['id'], #id
                    youtubeVideoMetadataData['ext'], #extension
                    youtubeVideoMetadataData['title'], #metadata title
                    youtubeVideoMetadataData['uploader'], #metadata author (for video)
                    youtubeVideoMetadataData['uploader'], #metadata artist (for music)
                    downloadDir, #download directory
                    youtubeVideoMetadataData['title'], #title
                    youtubeVideoMetadataData['ext'] #extension
                ))

                #delete the original file
                os.remove('{}/{} [{}].{}'.format(downloadDir, youtubeVideoMetadataData['title'], youtubeVideoMetadataData['id'], youtubeVideoMetadataData['ext']))
            
            #there was an error, tell the log for now, and add a way to tell the user there was an error soon
            except:
                print('Error downloading {} with quality {}.'.format(video[0], video[1]))
        
        #since the video queue is entirely downloaded, reset the queue
        videoQueue = []

        #wait half a second
        time.sleep(0.5)

#start the poller thread
_thread.start_new_thread(YTDL_POLLER, ())