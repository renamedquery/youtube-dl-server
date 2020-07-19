#import statements
import flask, json, requests

#add authentication via google authenticator

#try to import the config file
try:
    configData = json.loads(str(open('./config.json').read()))
#the config file does not exist, tell the user to run setup.py and then exit
except FileNotFoundError:
    print('No config file was detected. Are you running in the correct directory? Did you run setup.py?')
    exit()

#create the application class
app = flask.Flask(__name__)

#set up the directory tree
app._static_folder = './static'
app.template_folder = './templates'

#the function to handle any requests sent to the home page
@app.route('/', methods = ['GET', 'POST'])
def WEB_INDEX():

    #return the home page
    return flask.render_template('index.html', applicationName = configData['application_name'])

#the function to handle any requests sent to the queue page (only allow POST requests) this is where it triggers the server to download the media
@app.route('/queue', methods = ['POST'])
def WEB_QUEUE():

    #get the form data
    YTDL_URL = flask.request.form.get('url')
    YTDL_FORMAT = flask.request.form.get('format')

    #make a request to the url to check that it can be downloaded, if not return an error
    try:
        ytdlUrlRequestResponse = requests.get(url = YTDL_URL, params = {})
        if (ytdlUrlRequestResponse.status_code != 200): #status was not 200, so you probably cant download the video
            return flask.redirect(flask.url_for('WEB_ERROR'))
    #there was some sort of other error, also send them to the error page
    except:
        return flask.redirect(flask.url_for('WEB_ERROR'))

    #return the queue page
    return flask.render_template('queue.html', applicationName = configData['application_name'], vidURL = YTDL_URL, vidQualSet = YTDL_FORMAT)

#the function to handle any requests sent to the error page (usually because a video cant be downloaded)
@app.route('/error', methods = ['GET', 'POST'])
def WEB_ERROR():

    #return the error page
    return flask.render_template('error.html', applicationName = configData['application_name'])