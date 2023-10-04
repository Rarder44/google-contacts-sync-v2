
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

def EqualsTree(e1,e2):
    """ritorna true se gli alberi / array / oggeti  sono identici"""

    if type(e1)!= type(e2):
        return False
    
    elif type(e1) is list:
        if len(e1)!= len(e2):
            return False
        n = range(len(e1))
        for i in n:
            if EqualsTree(e1[i],e2[i])==False:
                return False
        
    elif type(e1) is dict:
        keys1=list(e1.keys())
        keys1.sort()
        keys2=list(e2.keys())
        keys2.sort()
        if keys1 != keys2:
            return False

        for k in keys1:
            if EqualsTree(e1[k],e2[k])==False:
                return False
            

    return True
    


def getUrlParameter(url,key):
    # Parsare l'URL
    parsed_url = urlparse(url)

    # Estrarre i parametri dall'URL
    params = parse_qs(parsed_url.query)

    if key in params:
        return params[key]
    return None

def setUrlParameter(url,key,value):

    # Parsare l'URL
    parsed_url = urlparse(url)

    # Estrarre i parametri dall'URL
    params = parse_qs(parsed_url.query)


    # Modificare il valore di un parametro (es. param1)
    params[key] = value     # [ value ]???

    # Ricreare l'URL con i parametri modificati
    updated_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        urlencode(params, doseq=True),  # Ricodifica i parametri
        parsed_url.fragment
    ))
    return updated_url