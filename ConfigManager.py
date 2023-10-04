import pathlib
import configparser
import datetime,pytz, dateutil
import dateutil.parser

class ConfigManager:
    def __init__(self,configFilePath :pathlib.Path | str):
        self.path=configFilePath
        self.data=[]
        self.load()

    
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
            self.data = configparser.ConfigParser()

            
            self.data["DEFAULT"] = {
                "msg": "You need an account section for each user, please setup",
                "last": "1970-01-01:T00:00:00+00.00",
                "backupdays": 0,
                "keyfile": f"{self.path.parent}/FIXME_keyfile.json",
            }
            self.data["account-1-FIXME"] = {
                "user": "FIXME@gmail.com",
            }
            self.data["account-2-FIXME"] = {
                "user": "FIXME@gmail.com",
            }

            with open(self.path, "w") as cfh:
                self.data.write(cfh)

            print(f"Made config file {self.path}, you must edit it")
            return False

        self.data = configparser.ConfigParser()
        self.data.read(self.path)
        if "account-FIXME" in self.data.sections():
            print(f"You must edit {self.path}.  There is an account-FIXME section")
            return False


        return True

    def __getitem__(self, key):
        return self.data[key]
        
    def getMails(self):
        return [ self.data[sectionKey]["user"]  for sectionKey in self.data.sections() if sectionKey.startswith("account-")]
    
    def getLastExecution(self):
        if "DEFAULT" in self.data and  "last" in self.data["DEFAULT"]:
            return dateutil.parser.isoparse(self.data["DEFAULT"]["last"])
        
        return dateutil.parser.isoparse("1970-01-01:T00:00:00+00.00") 
    
    def getAPI_JSON_path(self):
        return self.data["DEFAULT"]["APIjson_path"]