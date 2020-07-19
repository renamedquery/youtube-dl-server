#import statements
import flask, json

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

    #return the queue page
    return flask.render_template('queue.html', applicationName = configData['application_name'])