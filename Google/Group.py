import json
import copy
import re
from datetime import datetime
from Google.Shared import Shared

import dateutil.parser


from Utils.Logger import Logger,log
from  Utils.Utils import EqualsTree



class Group:
    def __init__(self,account) -> None:
        from Google.Account import Account
        self.account:Account.Account=account
        self.__body:dict =None
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
        
        g = Group(account)
        if "metadata" in googleObj and "updateTime" in googleObj["metadata"]:
            #tmp=datetime.strptime(googleObj["metadata"]["updateTime"], '%Y-%m-%dT%H:%M:%S.%fZ')    #funziona ma non compatibile con altre date usate nel codice
            tmp=dateutil.parser.isoparse(googleObj["metadata"]["updateTime"])
            g.updateTime= tmp

        g.__body=Group.__strip_body(googleObj)
        return g
    def fromResourceName(resourceName,account) :
        p = account.GoogleService.contactGroups().get(
            resourceName=resourceName,
            groupFields=','.join(Shared.group_field)
        ).execute()
        return Group.fromGoogleObj(p,account)
    def create(googleObj,account):

        googleObj =copy.deepcopy(googleObj)
        if "resourceName" in googleObj:     #in creazione viene essegnata dal server
            googleObj.pop("resourceName")
        if "formattedName" in googleObj:     #in creazione viene essegnata dal server
            googleObj.pop("formattedName")
        if "etag" in googleObj:     #in creazione viene essegnata dal server
            googleObj.pop("etag")
        if "groupType" in googleObj:     #in creazione viene essegnata dal server
            googleObj.pop("groupType")

        new_body = account.GoogleService.contactGroups().create(
            body={"contactGroup": {
                **googleObj
            }},
        ).execute()
        return Group.fromGoogleObj(new_body,account)
    
    def update(self):
        obj = self.account.GoogleService.contactGroups().update(
            resourceName=self.resourceName,
            body={
                "contactGroup": {
                    **self.__body
                },
                "updateGroupFields": ",".join(Shared.group_field),
                "readGroupFields":','.join(Shared.group_field)
            }
        ).execute()

         #recupero le modifiche appena applicate dal server e mi aggiorno il mio body
        tmp=Group.fromGoogleObj(obj,self.account)
        self.__body=tmp.__body 
        self.updateTime=tmp.updateTime



    def pull(self):
        c = Group.fromResourceName(self.resourceName,self.account)
        self.__body = c.__body

    def refreshEtag(self):
        c = Group.fromResourceName(self.resourceName,self.account)
        self.etag = c.etag
        
    def delete(self):
        self.account.GoogleService.contactGroups().delete(
            resourceName=self.resourceName,
            deleteContacts=False            
            ).execute()
        
    
    def equals(self, other):
        """controlla se un Contact è uguale ad un altro ( campo per campo )"""
        if not type(other)  is Group:
            return False
        
        
        body1=self.cloneBody()
        body2=other.cloneBody()

        #tolgo i campi che mi sfalsano il controllo
        body1.pop("etag")
        body2.pop("etag")

       
        #evito di controllare il resource name
        return EqualsTree(body1,body2)


    def copyFrom(self,other):
        """copia tutti i dati non specifici ( etag, resourceName,... ) da un altro Group"""
        assert isinstance(other,Group), "l'oggetto passato deve essere un gruppo"

        #sincronizzo tutti i campi che mi interessano
        self.name=other.name


        
    
    def cloneBody(self):
        cp=  copy.deepcopy(self.__body)
        return cp

    def clone(self):
        return Group.fromGoogleObj(self.cloneBody(),self.account)

    @property
    def resourceName(self):
        return self.__body["resourceName"]  
    
    @property
    def etag(self):
        return self.__body["etag"]   
    @etag.setter
    def etag(self, val):
        self.__body["etag"] = val

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
        self.__body["clientData" ]=newClientData         
    @syncTag.deleter
    def syncTag(self):
       self.syncTag=None


    @property
    def name(self):
        try:
            return self.__body["name"]
        except:
            return None
        
        #versione senza try catch
        """if "names" in self.__body and len(self.__body["names"]) >0 and "displayName" in self.__body[0]:
            return self.__body["names"][0]["displayName"]
        return None"""
    @name.setter
    def name(self, val):
        self.__body["name"]=val