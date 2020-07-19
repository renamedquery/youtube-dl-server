#import statements
import flask

#add a piece of code that makes sure that the config file is valid and if it isnt then it quits the program and tells the user to set up the app

#create the application class
app = flask.Flask(__name__)

#set up the directory tree
app._static_folder = './static'
app.template_folder = './templates'

#the function to handle any requests sent to the home page
@app.route('/', methods = ['GET', 'POST'])
def WEB_INDEX():

    return 'more coming soon'