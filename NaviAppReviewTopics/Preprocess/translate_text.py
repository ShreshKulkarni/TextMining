# -*- coding: utf-8 -*-
"""
Created on Fri Apr 13 17:47:04 2018

@author: Shreshtha Kulkarni
"""

import http.client, urllib.parse
from googletrans import Translator

# **********************************************
# *** Update or verify the following values. ***
# **********************************************

# Replace the subscriptionKey string value with your valid subscription key.
subscriptionKey = 'SUBSCRIPTION_KEY'

host = 'api.microsofttranslator.com'
path = '/V2/Http.svc/Translate'

#maxTranslations = "10"


body = ''

def Translate (text,to_language):

    headers = {
            'Ocp-Apim-Subscription-Key': subscriptionKey,
            'Content-type': 'text/xml'
            }
    conn = http.client.HTTPSConnection(host)
    params = "?to=" + to_language  + "&text=" + urllib.parse.quote (text)
    conn.request ("GET", path + params, body, headers)
    response = conn.getresponse ()
    result = response.read()
    #result_str = str(result.decode("utf-8")))
    trans_text = result.decode('utf-8').split(">")[1].split("<")[0]
    
    return trans_text

def translate_from_google(text):
    ts = Translator()
    text_trans = ts.translate(text).text
    return text_trans

