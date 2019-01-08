# -*- coding: utf-8 -*-
"""
Created on Thu Jan  3 05:18:07 2019

@author: Shreshtha Kulkarni
"""

import langdetect
import string
import re
import pandas as pd
import logging

#Import the previously cleaned data
df = pd.read_csv("../data/cleaned_data_w_translations.csv")

logging.basicConfig(filename='translation_info.log',level=logging.INFO)

#Check if there are any NaNs after emoji substitution. If yes, replace with BODY_NA and SUB_NA respectively.
#This will help us distinguish these substituions definitely.
df['Body_no_emoji'].fillna('BODY_NA',inplace=True)
df['Body_emoji_desc'].fillna('BODY_NA',inplace=True)
df['Subject_no_emoji'].fillna('SUB_NA',inplace=True)
df['Subject_emoji_desc'].fillna('SUB_NA',inplace=True)

#Dropping the rows where no text is available whatsoever
logging.info("DF rows before dropping = %d",df.shape[0])
df.drop(df[df['Translated Subject'].isnull() & df['Translated Body'].isnull() &(df.Body.isnull()) & (df.Subject.isnull()) ].index,axis=0,inplace=True)
logging.info("DF shape after dropping =%d",df.shape[0])

#Resetting index
df.reset_index(drop=True)

logging.info("Recs where the original reviews were lost during the scraping but translations were saved=%d",
             len(df[df.Body.isnull() & df.Subject.isnull() & 
                    (df['Translated Body'].notnull() | df['Translated Subject'].notnull())]))
#Finally No. of records which have translations present.
#It doesn't exclude the rows which are already in English and doesn't require translation thus
logging.info("Recs which do not require translation = %d",
             len(df[df['Translated Body'].notnull() | df['Translated Subject'].notnull()]))
logging.info("Recs which require translation = %d",
             len(df[(df['Translated Body'].isnull() & df['Translated Subject'].isnull()) 
             & (df.Body.notnull() | df.Subject.notnull())]))

#Adding a column to store final translations
final_translated_text = ['']*len(df)
df['Translated_Text'] = final_translated_text
df.reset_index(drop=True,inplace=True)
df.shape

#We need to filter out rows which do not really need translation to reduce the no. of translation queries
#Such rows can be 
#rows which are already in English, so we would need to detect language
#rows which have only ???? as a result of loss of data
#rows which have only email ids
#Append subject and body to reduce the no of queries
trans_reqd_count=0
en_count = 0
logging.info("Starting the loop to filter rows which do not require translation")
logging.info("#########################################################################")
for k in df.index:
    #import pdb;pdb.set_trace()
    lang=''
    text = ''
    text = str(df['Subject_emoji_desc'].iloc[k])+' '+str(df['Body_emoji_desc'].iloc[k])
    #To check whether it is a malformed string
    #First remove the BODY_NA and SUB_NA which was the text denoting NaNs for both columns
    #Then remove the email-ids followed by removal of standard english punctuations and numbers 
    #If the string is now composed of either only spaces or is null it must be a malformed string 
    #in which case it doesn't need to translated and hence marking its language as en
    text_temp = text.replace('BODY_NA','')
    text_temp = text_temp.replace('SUB_NA','')
    text_temp = re.sub(r"\w+@\w+\.com",'',text_temp)
    trans_tab = dict.fromkeys(map(ord, string.punctuation+string.digits), ' ')
    text_temp = text_temp.translate(trans_tab)
    if text_temp.isspace() or text_temp == '':
        #if k >= 100005 and k<200000:
            #import pdb;pdb.set_trace()
        logging.info("Malformed string in rec# %d: %s." ,k,text)
        df.set_value(col='Translated_Text',index=k, value = 'TRANS_NONE')
        continue
    
    try:
        lang = langdetect.detect(text) #To detect the reviews which were originally written in english
    except:
        logging.info("Language detection failed for %dth record. will translate anyway",k)
        lang = "LANG_NOT_FOUND"
    
    #Annotating the subject under xml tags <sub> so later on we can separate it.
    text = '<sub>'+str(df['Subject_emoji_desc'].iloc[k])+'</sub>'+str(df['Body_emoji_desc'].iloc[k])
    
    if lang == 'en':
        df.set_value(col='Translated_Text',index=k, value = text)
        en_count = en_count +1
    else:
        trans_sub = str(df['Translated Subject'].iloc[k])
        trans_body = str(df['Translated Body'].iloc[k])
        if (( trans_body !='nan' and trans_body.translate(trans_tab).strip() != "")| \
            (trans_sub !='nan' and trans_sub.translate(trans_tab).strip() != "")):
            #If translation is available append the same
            text = '<sub>'+trans_sub + '</sub>'+trans_body
            df.set_value(col='Translated_Text',index=k, value = text)
        else:
            #Mark it for translation
            df.set_value(col='Translated_Text',index=k, value = "TRANS_REQD")
            trans_reqd_count = trans_reqd_count +1
    if(k%50000 == 0):
        logging.info("Finished processing %d recs" ,k)
logging.info("#############################################################################################\n"+
             "Row filtering completed\n")

#Sanity Check
logging.info("Final no. of records that require translation=%d",
             len([w for w in df['Translated_Text'] if w == 'TRANS_REQD']))
logging.info("Records that do not need translation mostly because there is no text worth translating=%d",
             len([w for w in df['Translated_Text'] if w == 'TRANS_NONE']))
logging.info("Any NaNs or empty recs=%d",len([w for w in df['Translated_Text'] if w == '' or w is None]))
logging.info(df['Translated_Text'].head(5))

#Save it to a file so we don't need to run the time consuming loop again
df.to_csv("../data/cleaned_lang_trans_temp.csv")

#Translate using Microsoft Translation Service
import translate_text

success_count = 0
failed_count = 0
logging.info("Starting Microsoft Translation loop\n#############################################################")
for k in df.index:
    
    if df['Translated_Text'].iloc[k] != 'TRANS_REQD':
        continue
    
    text = '<sub>'+str(df['Subject_emoji_desc'].iloc[k]) +'</sub>'+str(df['Body_emoji_desc'].iloc[k])
    trans_text = translate_text.Translate(text,'en-us')
    if(trans_text is None or trans_text == '' or trans_text.isspace()):
        logging.info("Translation Failed for rec %d : %s." ,k,text)
        failed_count= failed_count+1
    else:
        #import pdb;pdb.set_trace()
        trans_text = trans_text.replace('&lt;','<').replace('&gt;','>')
        df.set_value(col='Translated_Text',index=k, value = trans_text)
        success_count = success_count+1
    if(k%20000 == 0):
        logging.info("Finished processing %d recs" ,k)

logging.info("Successful translation count= %d\n Failed translation count = %d" ,success_count, failed_count)
logging.info("Finished Microsoft Translation loop\n#############################################################\n")
             
#saving to temp file so don't have to run again
df.to_csv("../data/cleaned_data_final_trans_v0.1.csv")

'''We can see that the translation fails where the review is just a few words long. 
This might be because the translation algorithm provided by Microsoft is not as strong for fewer characters 
or they don't have profile for a particular language. 
We can try to translate the remaining text with help of google APIs, 
although it comes with a caveat of throwing unreliable responses after a while.'''
from googletrans import Translator

ts = Translator()
success_count = 571
failed_count = 475
it=[]
trans_reqd_dict = dict('<sub>'+df[df.Translated_Text == 'TRANS_REQD']['Subject_emoji_desc'] +'</sub> '
                       + df[df.Translated_Text == 'TRANS_REQD']['Body_emoji_desc'])

logging.info("Starting google translation loop\n###############################################\n")
for i in list(trans_reqd_dict.keys()):
    #import pdb; pdb.set_trace()
    if(i <=360247 ):
        continue
    
    if len(trans_reqd_dict[i].split()) < 3:
        logging.info("Translation Failed for rec %d : %s." ,i,trans_reqd_dict[i])
        failed_count= failed_count+1
        continue
    
    try:
        a = ts.translate(trans_reqd_dict[i]).text
        if len(a )> 0:
            trans_reqd_dict[i] = a
            success_count = success_count + 1
        else:
            logging.info("Translation Failed for rec %d : %s." ,k,text)
            failed_count= failed_count+1
    except:
        logging.info("Successful translation count= %d\n Failed translation count = %d" ,success_count, failed_count)

logging.info("Successful translation count= %d\n Failed translation count = %d" ,success_count, failed_count)
logging.info("Finished google translation loop\n###############################################\n")

#separate the subject and body from annotated translations
df['Trans_sub'] = [w.split('<sub>')[1].split('</sub>')[0] if w.find('<sub>') != -1 else w for w in df['Translated_Text'] ]
df['Trans_body'] = [w.split('<sub>')[1].split('</sub>')[1] if w.find('<sub>') != -1 else w for w in df['Translated_Text'] ]

df.shape

df.reset_index(drop=True,inplace=True)

#separate text and subject from google translated items
j=0
for i in list(trans_reqd_dict.keys()):
    
    #print(trans_reqd_dict[i])
    
    myStr= trans_reqd_dict[i]
    trans_body = ''
    trans_sub = ''
    
    regObj = re.search('<.*>',myStr,re.IGNORECASE)
    if regObj is not None and regObj.span()[0] == 0 and len(regObj.span()) == 2:
        trans_body = myStr[regObj.span()[1]: len(myStr)]
        tempStr = myStr[regObj.span()[0] : regObj.span()[1]]
        rm1 = re.search('>.*<',tempStr,re.IGNORECASE)
        if rm1 is not None:
            trans_sub = tempStr[rm1.span()[0]+1 : rm1.span()[1]-1]
        else:
            trans_sub = ''
    elif regObj is not None and regObj.span()[0] >0 and len(regObj.span()) == 2:
        #import pdb; pdb.set_trace()
        if(regObj.span()[1] == len(myStr)):
            tempStr = myStr[0:regObj.span()[0]]
            rm1 = re.search('>',tempStr,re.IGNORECASE)
            if rm1 is None:
                trans_body = tempStr
                tempStr = myStr[regObj.span()[0]:regObj.span()[1]]
                rm2 = re.search('>.*<',tempStr,re.IGNORECASE)
                if rm2 is not None:
                    trans_sub = tempStr[rm2.span()[0]+1 : rm2.span()[1]-1]
            else:
                trans_body = tempStr[0:rm1.span()[0]]
        else:
            trans_body = myStr[regObj.span()[1]:len(myStr)]
        
            tempStr=myStr[0:regObj.span()[0]]
            rm1 = re.search('>',tempStr,re.IGNORECASE)
            if rm1 is not None:
                trans_sub = tempStr[rm1.span()[1]:len(tempStr)]
            else:
                trans_sub = myStr[0:regObj.span()[0]]
    else:
        logging.info("Failed while parsing text %s" ,myStr)
        trans_body = re.sub('<.*SUB_NA.*>','',myStr)
        trans_sub='SUB_NA'
        
    
    df.set_value(col='Trans_sub',index=i,value=trans_sub)
    df.set_value(col='Trans_body',index=i,value=trans_body)
    
    j= j+1
    if(i%1000 == 0):
        logging.info("Processed %d recs" ,j)

logging.info("Sanity Check###############################\n")
logging.info("Recs that were marked not to be translated due to malformed string=%d\n",len(df[df.Trans_body == 'TRANS_NONE']))
logging.info("Recs where subject is not available=%d\n",len(df[df.Trans_sub == 'SUB_NA']))
logging.info("Recs where body text is not available=%d\n",len(df[df.Trans_body == 'BODY_NA']))
logging.info("Rec  where subject was lost in parsing the annotated text=%d\n",len(df[df.Trans_sub == '']))
logging.info("Recs where text was lost due to parsing the annotated text=%d\n",len(df[df.Trans_body == '']))
logging.info("Untranslated recs=%d\n",len(df[df.Translated_Text == 'TRANS_REQD']))

#It might be where subject was lost in parsing the annotated text but since it is one rec marking it SUB_NA
df.set_value(col='Trans_sub',index=df[df.Trans_sub == ''].index ,value= 'SUB_NA')

#Saving the final set
df.to_csv("../data/cleaned_data_final_trans_v2.csv")

