import pathlib
import configparser
import datetime,pytz, dateutil
import dateutil.parser

from  Utils.Logger import log
class ConfigManager:
    def __init__(self,configFilePath :pathlib.Path | str):
        self.path=configFilePath
        self.data=[]
        self.isLoaded=self.load()

    
    def save(self):
        #aggiorno la data dell'ultimo salvataggio
        self.data.set('DEFAULT', 'last',   (datetime.datetime.utcnow() + datetime.timedelta(seconds=5)).replace(tzinfo=pytz.utc).isoformat()   )     
        with open(self.path, "w") as cfh:
            self.data.write(cfh)

    def load(self):

        if type(self.path) is str:
            self.path = pathlib.Path(self.path)
        
        assert not type(self.path) is pathlib.Path, "wrong type for 'confFile' parameter"
            
        

        if not self.path.exists():
            self.data = configparser.ConfigParser(allow_no_value=True)

            self.data["DEFAULT"] = {
                ";You need an account section for each user, please setup":"",
                "last": "1970-01-01T00:00:00.00+00:00",
                ";0 = backup disabled | 1 or more = backup number that are kept":"",
                "backup_history": 0,
                "APIjson_path": f"{self.path.parent}/GoogleAPI.json",
                ";Enable or disable the synchronization of profile photos":"",
                "photo_sync":True
            }
            self.data["account-1-FIXME"] = {
                "user": "FIXME@gmail.com",
            }
            self.data["account-2-FIXME"] = {
                "user": "FIXME@gmail.com",
            }

            with open(self.path, "w") as cfh:
                self.data.write(cfh)

            log(f"Made config file {self.path}, you must edit it")
            return False

        self.data = configparser.ConfigParser()
        self.data.read(self.path)
        if "account-1-FIXME" in self.data.sections() or "account-2-FIXME" in self.data.sections():
            log(f"You must edit {self.path}.  There is an account-FIXME section")
            return False


        return True

    def __getitem__(self, key):
        return self.data[key]
        
    def getMails(self):
        return [ self.data[sectionKey]["user"]  for sectionKey in self.data.sections() if sectionKey.startswith("account-")]
    
    def getLastExecution(self):
        if "DEFAULT" in self.data and  "last" in self.data["DEFAULT"]:
            return dateutil.parser.isoparse(self.data["DEFAULT"]["last"])
        
        return dateutil.parser.isoparse("1970-01-01T00:00:00.00+00:00") 
    
    def getAPI_JSON_path(self):
        return self.data["DEFAULT"]["APIjson_path"]