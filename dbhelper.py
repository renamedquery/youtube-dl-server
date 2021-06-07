# a module to help out with communication to the database

import sqlite3, logger
import werkzeug.security as WZS

class dbhelper:

    dbcur = None # database cursor
    dbconn = None # database connection

    def __init__(self, database_location) -> None:

        self.dbconn = sqlite3.connect(database_location)
        self.dbcur = self.dbconn.cursor()
        logger.log('SUCCESSFULLY CONNECTED TO THE DATABASE. DID NOT VERIFY INTEGRITY OF CONTENTS.')
        return None        
    
    def run(self, query, queryQuestionMarkTitles) -> list:

        logger.log('EXECUTING QUERY.')
        return self.dbconn.execute(query, tuple(queryQuestionMarkTitles)).fetchall()
    
    # flaskSesison should be [username, password] unhashed
    def checkAuthStatus(self, flaskSession):

        dbPasswordHash = self.run('SELECT password FROM users WHERE username = ?', [flaskSession[0],])
        return WZS.check_password_hash(dbPasswordHash[0][0], flaskSession[1])