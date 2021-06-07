# a module to help out with communication to the database

import sqlite3, logger

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