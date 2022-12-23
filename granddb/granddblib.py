import psycopg2
import psycopg2.extras
from sshtunnel import SSHTunnelForwarder
import numpy
import grand.io.root_trees
import re

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import func
from sqlalchemy.inspection import inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects import postgresql


def casttodb(value):
    if isinstance(value, numpy.uint32):
        value = int(value)
    if isinstance(value, numpy.float32):
        value = float(value)
    if isinstance(value, numpy.ndarray):
        if value.size == 0:
            value = None
        elif value.size == 1:
            value = value.item()
        else:
            value = value.tolist()
    if isinstance(value, grand.io.root_trees.StdVectorList):
        value = [i for i in value]
    if isinstance(value, str):
        value = value.strip().strip('\t').strip('\n')
    return value


## @brief Class to handle the Grand database.
# A simple psycopg2 connexion (dbconnection) or a sqlalchemysession (sqlalchemysession) can be used
class Database:
    _host: str
    _port: int
    _dbname: str
    _user: str
    _passwd: str
    _sshserver: str
    _sshport: int
    _tables = {}
    dbconnection = None  # psycopg2 connect
    sqlalchemysession = None  # sqlalchemy session

    # _cred : Credentials

    def __init__(self, host, port, dbname, user, passwd, sshserv="", sshport=22, cred=None):
        self._host = host
        if port == "":
            self._port = 5432
        else:
            self._port = port
        self._dbname = dbname
        self._user = user
        self._passwd = passwd
        self._sshserv = sshserv
        if sshport == "":
            self._sshport = 22
        else:
            self._sshport = sshport
        self._cred = cred

        if self._sshserv != "" and self._cred is not None:
            self.server = SSHTunnelForwarder(
                (self._sshserv, self._sshport),
                ssh_username=self._cred.user(),
                ssh_pkey=self._cred.keyfile(),
                remote_bind_address=(self._host, self._port)
            )
            self.server.start()
            local_port = str(self.server.local_bind_port)
            self._host = "127.0.0.1"
            self._port = local_port

        #self.connect()

        engine = create_engine(
            'postgresql+psycopg2://' + self.user() + ':' + self.passwd() + '@' + self.host() + ':' + self.port() + '/' + self._dbname)
        Base = automap_base()

        Base.prepare(engine, reflect=True)
        self.sqlalchemysession = Session(engine)
        for table in engine.table_names():
            self._tables[table] = getattr(Base.classes, table)

    def __del__(self):
        # self.session.flush()
        # self.session.close()
        self.dbconnection.close()
        # self.server.stop(force=True)

    def connect(self):
        self.dbconnection = psycopg2.connect(
            host=self.host(),
            database=self.dbname(),
            port=self.port(),
            user=self.user(),
            password=self.passwd())

    def disconnect(self):
        self.dbconnection.close()

    def host(self):
        return self._host

    def port(self):
        return self._port

    def dbname(self):
        return self._dbname

    def user(self):
        return self._user

    def passwd(self):
        return self._passwd

    def sshserv(self):
        return self._sshserv

    def sshport(self):
        return self._sshport

    def cred(self):
        return self._cred

    def tables(self):
        return self._tables

    def select(self, query):
        try:
            self.connect()
            cursor = self.dbconnection.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(query)
            record = cursor.fetchall()
            cursor.close()
        except psycopg2.DatabaseError as e:
            print(f'Error {e}')
        return record

#    def insert(self, query):
#        record = []
#        try:
#            cursor = self.dbconnection.cursor(cursor_factory=psycopg2.extras.DictCursor)
#            cursor.execute(query)
#            print(cursor.statusmessage)
#            self.dbconnection.commit()
#            record.append(cursor.fetchone()[0])
#            cursor.close()
#        except psycopg2.DatabaseError as e:
#            print(f'Error {e}')
#        return record
#
#    def insert2(self, query, values):
#        record = []
#        try:
#            cursor = self.dbconnection.cursor(cursor_factory=psycopg2.extras.DictCursor)
#            cursor.execute(query, values)
#            print(cursor.statusmessage)
#            self.dbconnection.commit()
#            record.append(cursor.fetchone()[0])
#            cursor.close()
#        except psycopg2.DatabaseError as e:
#            print(f'Error {e}')
#        return record

    ## @brief Method to get the list of the repositories defined in the database.
    # Returns a dictionary with
    # repository - character varying - name of the repo
    # path - character varying - list of paths where files can be searched for
    # server - character varying - name or IP of the server,
    # port - integer - port to access the server
    # protocol - character varying - protocol name to access the server
    # id_repository - integer - id_repository
    def get_repos(self):
        record = None
        # Intergogation using simple psycopg2 query to directly get a dict
        query = "select * from get_repos()"
        record = self.select(str(query))
        return record

    ## @brief For parameter <param> of value <value> in table <table> this function will check if the param is a foreign key and if yes it will
    # search de corresponding id in the foreign table. If found, it will return it, if not, it will add the parameter in the foreign table
    # and return the id of the newly created record.
    def get_or_create_fk(self, table, param, value):
        idfk = None
        if value is not None and value != "":
            # Check if foreign key
            if getattr(self._tables[table], param).foreign_keys:
                # Get the foreign table and id in this table
                # ugly but couldn't find another way to do it !
                fk = re.findall(r'\'(.+)\.(.+)\'', str(list(getattr(self._tables[table], param).foreign_keys)[0]))
                fktable = fk[0][0]  # foreign table
                # fkfield = fk[0][1]  # id field in foreign table
                idfk = self.get_or_create_key(fktable, fktable, value, 'autoadd')
        return idfk

    ## @brief Search in table <table> if we have a record with <value> for field <field>.
    # If yes, returns id_<table>, if not create a record and return the id_<table> for this record
    def get_or_create_key(self, table, field, value, description=""):
        idfk = None
        if value is not None and value != "":
            filt = {}
            filt[field] = str(casttodb(value))
            ret = self.sqlalchemysession.query(getattr(self._tables[table], 'id_' + table)).filter_by(**filt).all()
            if len(ret) == 0:
                filt['description'] = description
                container = self.tables()[table](**filt)
                self.sqlalchemysession.add(container)
                self.sqlalchemysession.flush()
                idfk = int(getattr(container, 'id_' + table))
            else:
                idfk = int(ret[0][0])

        return idfk

    ## @brief Function to register a repository (if necessary) in the database.
    # Returns the id_repository of the corresponding repository
    def register_repository(self, name, protocol, port, server, path, description=""):
        # Check protocol
        savepoint = self.sqlalchemysession.begin_nested()
        id_protocol = self.get_or_create_key('protocol', 'protocol', protocol, description)
        id_repository = self.get_or_create_key('repository', 'repository', name, description)
        self.sqlalchemysession.flush()
        # Check if repository access exists or not !
        repo_access = self.sqlalchemysession.query(self.tables()['repository_access']
                                                   ).filter_by(id_repository=id_repository,
                                                               id_protocol=id_protocol).first()
        if repo_access is not None:
            if set(repo_access.path) == set(path):
                pass
            else:
                repo_access.path = path
                self.sqlalchemysession.commit()
        else:
            repository_access = {'id_repository': id_repository, 'id_protocol': id_protocol, 'port': port,
                                 'server_name': server, 'path': path}
            container = self.tables()['repository_access'](**repository_access)
            self.sqlalchemysession.add(container)
            self.sqlalchemysession.flush()
            #self.sqlalchemysession.commit()
        savepoint.commit()
        return id_repository

    ## @brief Function to register (if necessary) a file into the database.
    # It will first search if the file is already known in the DB and check the repository.
    # Returns the id_file for the file and a boolean True if the file was not previously in the DB (i.e it's a new file)
    # and false if the file was already registered. This is usefull to know if the metadata of the file needs to be read
    # or not
    def register_file(self, filename, newfilename, id_repository, provider):
        import os
        register_file = False
        isnewfile = False
        idfile = None
        ## Check if file not already registered IN THIS REPO : IF YES, ABORT, IF NO REGISTER
        file_exist = self.sqlalchemysession.query(self.tables()['file']).filter_by(
            filename=os.path.basename(newfilename)).first()
        if file_exist is not None:
            file_exist_here = self.sqlalchemysession.query(self.tables()['file_location']).filter_by(
                id_repository=id_repository).first()
            if file_exist_here is None:
                # file exists in different repo. We only need to register it in the current repo
                register_file = True
                idfile = file_exist.id_file
        else:
            # File not registered
            register_file = True
            isnewfile = True

        ### Register the file
        if register_file:
            id_provider = self.get_or_create_key('provider', 'provider', provider)
            if isnewfile:
                container = self.tables()['file'](filename=os.path.basename(newfilename),
                                                           description='ceci est un fichier',
                                                           original_name=os.path.basename(filename),
                                                           id_provider=id_provider)
                self.sqlalchemysession.add(container)
                self.sqlalchemysession.flush()
                idfile = container.id_file
            container = self.tables()['file_location'](id_file=idfile, id_repository=id_repository)
            self.sqlalchemysession.add(container)
            self.sqlalchemysession.flush()
        return idfile, isnewfile
