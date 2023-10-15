from googleapiclient.http import HttpRequest
from googleapiclient.http import HttpError
from time import sleep
from Utils.Logger import log,Logger

def patch():
    """permette di pathare (Monkey patch) la funzione execute in modo da implemenmtare il retrasmission in caso di 429 ( quota exceded )"""
    #non uso la funzionalità base dell'execute per impostare il numero di ritrasmissioni perchè voglio vedere nel dettaglio che succede 
    #e in base al tipo di errore, agire in modo differente


    #TODO implemento il retry solo in caso dell'eccezione 429
    oldExecute=HttpRequest.execute

    def _new_execute(self,baseRTO=0.5,maxRTO=None):
        Rto=baseRTO
        times=1
        while True:
            try:
                ret = oldExecute(self)
                return ret
            except HttpError as e:
                if e.status_code!=429:
                    raise e
            
                log.err("ERR quota")        # per dettagli aggiungere  ",e" nei parametri
                log(f"retry ({times} time)...")
                times+=1
            except Exception as e:
                raise e
            
            
            newRTO=Rto*2
            if maxRTO!=None and newRTO > maxRTO:
                raise Exception("loop reached the maximum RTO")
            sleep(Rto)
            Rto=newRTO

    HttpRequest.execute=_new_execute

    pass
