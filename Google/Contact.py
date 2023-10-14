import json
import copy
import re
from Google.Shared import Shared
import Google.Account
import dateutil.parser
import base64
import requests
from  Utils.Utils import EqualsTree

class Contact:
    def __init__(self,account) -> None:
        self.__body:dict =None
        self.account:Google.Account.Account=account
        self.updateTime=None
        

    def __strip_body(body):
        #cancello tutti i metadata dal contatto ( non servono per la sync )
        def recursiveDeleteAllMetadata(obj):
            if type(obj) is dict: 
                if "metadata" in obj:
                    obj.pop("metadata")
                for k in obj:
                    recursiveDeleteAllMetadata(obj[k])
            if type(obj) is list:
                for o in obj:
                    recursiveDeleteAllMetadata(o)
        recursiveDeleteAllMetadata(body)
        return body

    def fromGoogleObj(googleObj,account):
        assert "resourceName" in googleObj, f"the object is not a valid Contact: {googleObj}"
        assert "etag" in googleObj, f"the object is not a valid Contact: {googleObj}"
        assert "names" in googleObj, f"the object is not a valid Contact: {googleObj}"
        

        c = Contact(account)
        if "metadata" in googleObj and "sources" in googleObj["metadata"]:
            for s in googleObj["metadata"]["sources"]:
                if "updateTime" in s:
                    #tmp=datetime.strptime(s["updateTime"], '%Y-%m-%dT%H:%M:%S.%fZ')
                    tmp=dateutil.parser.isoparse(s["updateTime"])
                    
                    
                    if c.updateTime==None or tmp > c.updateTime:
                        c.updateTime= tmp

        c.__body=Contact.__strip_body(googleObj)

        return c
    def fromResourceName(resourceName,account) :
        p = account.GoogleService.people().get(
            resourceName=resourceName,
            personFields=','.join(Shared.all_person_fields)
        ).execute()
        return Contact.fromGoogleObj(p,account)
    def create(googleObj,account):

        #in creazione alcuni campi danno problemi...
        keysToDelete=["photos","resourceName","etag"]
        for k in keysToDelete:
            if k in googleObj:
                googleObj.pop(k)

     

        new_body = account.GoogleService.people().createContact(
            body=googleObj,
            personFields=','.join(Shared.all_person_fields)
        ).execute()
        return Contact.fromGoogleObj(new_body,account)

    def update(self):

        obj = self.account.GoogleService.people().updateContact(
            resourceName=self.resourceName,
            updatePersonFields=','.join(Shared.all_update_person_fields),
            personFields=','.join(Shared.all_person_fields),
            body=self.__body
        ).execute()

        #recupero le modifiche appena applicate dal server e mi aggiorno il mio body
        tmp=Contact.fromGoogleObj(obj,self.account)
        self.__body=tmp.__body 
        self.updateTime=tmp.updateTime

    def updatePhoto(self,photoBytes):
        obj = self.account.GoogleService.people().updateContactPhoto(
            resourceName=self.resourceName,
            body={
                "photoBytes": base64.b64encode(photoBytes).decode('utf-8'),
                "personFields": ','.join(Shared.all_person_fields),
            }
        ).execute()

        #recupero le modifiche appena applicate dal server e mi aggiorno il mio body
        tmp=Contact.fromGoogleObj(obj["person"],self.account)
        self.__body=tmp.__body 
        self.updateTime=tmp.updateTime


    def pull(self):
        c = Contact.fromResourceName(self.resourceName,self.account)
        self.__body = c.__body

    def refreshEtag(self):
        c = Contact.fromResourceName(self.resourceName,self.account)
        self.etag = c.etag
        
    def delete(self):
        self.account.GoogleService.people().deleteContact(resourceName=self.resourceName).execute()
        
    def deletePhoto(self):
        obj = self.account.GoogleService.people().deleteContactPhoto(
            resourceName=self.resourceName,
            personFields=','.join(Shared.all_person_fields)
            ).execute()
        
        #recupero le modifiche appena applicate dal server e mi aggiorno il mio body
        tmp=Contact.fromGoogleObj(obj["person"],self.account)
        self.__body=tmp.__body 
        self.updateTime=tmp.updateTime

        
    
    def equals(self, other):
        """controlla se un Contact è uguale ad un altro ( campo per campo )"""
        if not type(other)  is Contact:
            return False
        
        
        body1=self.cloneBody()
        body2=other.cloneBody()

        #tolgo i campi che mi sfalsano il controllo
        body1.pop("etag")
        body2.pop("etag")

        #il controllo delle foto lo posso fare solo scaricando le foto di ogni utente ( troppo dispendioso? le tengo in cache? )
        body1.pop("photos")
        body2.pop("photos")

        #le membership devo controllarle 
        body1.pop("memberships")
        body2.pop("memberships")

        
        #evito di controllare il resource name
        return EqualsTree(body1,body2)

        pass


    
    def cloneBody(self):
        cp=  copy.deepcopy(self.__body)
        return cp

    def copyFrom(self,other):
        """copia tutti i dati non specifici ( etag, resourceName,... ) da un altro contatto"""
        assert isinstance(other,Contact), "l'oggetto passato deve essere un contatto"

        #sincronizzo tutti i campi che mi interessano
        #o meglio prendo il nuovo body e ci sposto i campi che devono rimanere invariati
        toKeep=["resourceName","etag","memberships"]      #memberships la gestisco a parte
        correctBody= other.cloneBody()
        for key in toKeep:
            if key in self.__body:
                correctBody[key]= self.__body[key]

        self.__body=correctBody

    def copyMembership(self,other):
        """permette di copiare i dati della membership usando il SyncTag per sincronizzare i gruppi nei diversi account"""
        assert isinstance(other,Contact), "l'oggetto passato deve essere un contatto"

        groupsSyncTags=other.getGroupsSyncTags()
        self.setGroupsBySyncTags(*groupsSyncTags)




    def setGroupsBySyncTags(self,*GroupsSyncTags):
        """accetta una lista di syncTag relativa ai gruppi da cercare nell'account per recuperare i resourceName da settare nel Contact"""
        groups = [ self.account.getGroupBySyncTag(g) for g in GroupsSyncTags]

        #TODO: se uno dei gruppi è None vuol dire che non è il syncTag e dovrebbe essere un errore! do eccezione o vado avanti?
        assert not None in groups,"errore durante il recupero del resourceName di un gruppo dal SYNC_TAG"

        GroupsResourceNames =[ g.resourceName for g in groups ]

        self.setGroupsByResourceNames(*GroupsResourceNames)

        pass

    def setGroupsByResourceNames(self,*GroupsResourceNames):
        """accetta una lista di ResourceNames relativa ai gruppi da settare nel Contact\n
        Se non viene passato nulla, il Contatto viene rimosso da tutti i gruppi 
        """

        self.__removeAllGroups()
        newMemberships=[]

        assert not None in GroupsResourceNames,"errore durante l'assegnazione dei gruppi ad un Contact, un Group.resourceName è a None"
        

        for groupResourceName in GroupsResourceNames:

            groupID = re.sub(r'^contactGroups/', "", groupResourceName)
            newMemberships.append(
                {
                    "contactGroupMembership": {
                        "contactGroupId": groupID,
                        "contactGroupResourceName": groupResourceName,
                    }
                }
            )

        self.__body["memberships"] = self.__body["memberships"]+newMemberships
        
    def getGroupsSyncTags(self):
        """recupera i SyncTag di tutti i gruppi in cui è inserito"""
        groupResourceNames= [ "contactGroups/"+m["contactGroupMembership"]["contactGroupId"]    for m in self.__body["memberships"]    if m["contactGroupMembership"]["contactGroupId"] not in Shared.group_id_not_to_sync ]
        groups=self.account.getGroupsByResourceNames(*groupResourceNames)
        groupSyncTags=[  g.syncTag   for g in groups]
        
        if len(groupSyncTags) == len(groupResourceNames):
            return groupSyncTags
        
        raise Exception("ERR! non è stato possibile recuperare il SyncTag di un gruppo, assicurati di aver prima effettuato il sync dei gruppi prima dei contatti")

    def __removeAllGroups(self):
        self.__body["memberships"] = [
                grp
                for grp in self.__body["memberships"]
                if (
                    "contactGroupMembership" in grp
                    and grp["contactGroupMembership"]["contactGroupId"] in Shared.group_id_not_to_sync
                )
            ]

        

     
        

    @property
    def groups(self):
        """ritorna i gruppi in cui è l'utente (rn + syncTag) """
        if not "memberships" in self.__body:
            return []
        
        #TODO: controllo che id e resourceTag sono forse direttamente collegati, non serve ritornarli entrambi
        temp = [ 
                    {
                        "id": el["contactGroupMembership"]["contactGroupId"],
                        "resourceName":el["contactGroupMembership"]["contactGroupResourceName"],
                        "SYNC_TAG":self.account.getGroupByResourceName (el["contactGroupMembership"]["contactGroupResourceName"])
                    }
                  
                    for el in self.__body["memberships"]  
                ]
        
        return temp
        
        
    @property
    def resourceName(self):
        return self.__body["resourceName"]  
    #@resourceName.setter
    #def resourceName(self, val):
    #    self.__body["resourceName"] = val
    #@resourceName.deleter
    #def resourceName(self):
    #   self.__body.pop("resourceName")



    @property
    def etag(self):
        return self.__body["etag"]   
    @etag.setter
    def etag(self, val):
        self.__body["etag"] = val
    #@etag.deleter
    #def etag(self):
    #   self.__body.pop("etag")


    @property
    def memberships(self):
        return self.__body["memberships"]   
    @memberships.setter
    def memberships(self, val):
        self.__body["memberships"] = val
    @memberships.deleter
    def memberships(self):
       self.__body.pop("memberships")


    @property
    def syncTag(self):
        if not "clientData" in self.__body:
            return None
        find = [el for el in self.__body["clientData"] if el["key"]==Shared.SYNC_TAG]
        if len(find)==0:
            return None
        if len(find)>1:
            raise Exception(f"l'utente {self.resourceName} ha 2 SYNC_TAG!!! controllare!!")
        
        return find[0]["value"]
    @syncTag.setter
    def syncTag(self, val):
        #prendo tutto il clientData ( se c'è ), escluso il SYNC_TAG  
        newClientData = [
                    i
                    for i in self.__body.get('clientData', [])
                    if i.get('key', None) != Shared.SYNC_TAG
                ]
        if val!=None:
            newClientData.append({'key': Shared.SYNC_TAG, 'value': val})

        #nel caso in cui non ci siano altri elementi nel clientData, facendo quindi un update con clientData=[]
        #l'update non viene fatto
        #quindi passo una key e un value fuffi, giusto per fagli fare l'update
        if len(newClientData)==0:                                      
            newClientData.append({'key': "---", 'value': "---"})        


        self.__body["clientData" ]=newClientData

    @syncTag.deleter
    def syncTag(self):
       self.syncTag=None


    @property
    def name(self):
        try:
            return self.__body["names"][0]["displayName"]
        except:
            return None
        
        #versione senza try catch
        """if "names" in self.__body and len(self.__body["names"]) >0 and "displayName" in self.__body[0]:
            return self.__body["names"][0]["displayName"]
        return None"""


    @property
    def photo(self):
        if not "photos" in self.__body:
            return None
        
        if len(self.__body["photos"])==0:
            return None
        
        if len(self.__body["photos"])>1:
            raise Exception("TODO: gestire un account con più foto?!?!?")
        
        if "default" in self.__body["photos"][0]:     #immagine che viene messa in automatico, non mi interessa
            return None
        
        return self.__body["photos"][0]["url"]

    @property 
    def photoBytes(self):

        #google usa un metodo suo per definire la dimensione della foto da visualizzare ( non è un parametro )
        #alla fine dell'url c'è un = con "S" e la dimensione.
        #mettendo un numero molto più grande della dimensione viene ritornata l'immagine a dimensione reale
        #tolgo quindi qualsiasi cosa che c'è dopo l'uguale e ci metto "s10000"

        if not self.photo:
            return None
        equal_position = self.photo.find("=")
        if equal_position == -1:
            return None
        urlFullSize = self.photo[:equal_position + 1]+"s10000"      
        response = requests.get(urlFullSize)       #prendo la foto a dimensione "grande" TODO: parso l'url e modifico il parametro in corretto
        return bytearray(response.content)       #recupero l'array di byte
        

    def exportJSON(self,includeImage=False):
        """crea un json object che contiene tutti i dati necessari per un backup"""

        obj=   {"body":self.__body,"updateTime":self.updateTime.isoformat()}
        if includeImage:
            _bytes= self.photoBytes
            if _bytes:
                obj["photoBytes"]=base64.b64encode(_bytes).decode('utf-8')

        return obj
        

        


    def __str__(self) -> str:
        return json.dumps(self.__body)
    
    def __repr__(self) -> str:
        return self.__str__()