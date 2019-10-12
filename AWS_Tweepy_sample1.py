import tweepy as tw
import pandas as pd
import boto3
import os
import matplotlib.pyplot as plt

# OAuth2 authentification for twitter
# Define CONS_KEY, CONS_SECRET, ACCESS_KEY and ACCESS SECRET as environmental variables and get their values using os.getenv()
auth = tw.OAuthHandler(os.getenv('CONS_KEY'), os.getenv('CONS_SECRET'))
auth.set_access_token(os.getenv('ACCESS_KEY'), os.getenv('ACCESS_SECRET'))
api = tw.API(auth, wait_on_rate_limit = True)

# Define query conditions.
# Refer to https://developer.twitter.com/en/docs/tweets/rules-and-filtering/overview/standard-operators
search_word = '"QUERY_PHRASE/WORD" -filter:retweets -filter:replies filter:safe'
since_date = '2019-10-01'
search_type = 'recent' #select from 'recent', 'popular', or 'mixed'
num_tweets = 5

# Search and get tweets 
tweets = tw.Cursor(api.search, 
                   q=search_word, 
                   since=since_date,
                   result_type=search_type
                   #lang='ja' # turn on to search by language
                  ).items(num_tweets)

text_list = []
sentiment_list = []
lang_list = []
location_list = []

# for each tweet
for tweet in tweets:
    text = tweet.text
    lang = tweet.lang
    
    # break tweet to text + https link and extract only text 
    if len(tweet.entities['urls'])!=0:
        text = text.split(' https://')[0].strip() # remove whitespace at front and back
        
    if text in text_list: # Skip the following if text matches any one in the list
        continue        
    
    text_list.append(text)
    lang_list.append(tweet.lang) # original language before translation
    location_list.append(tweet.user.location) # user location

    # setup AWS boto3 clients
    # Define ACCESS_KEY and ACCESS_SECRET as environmental variables/or you may define them as arguments of the following methods
    comprehend = boto3.client('comprehend')
    translate = boto3.client('translate')
    
    # if tweet not in the language list of .detect_sentiment method, translate text to English 
    lang_choice = ['en','es','fr','de','it','pt']
    if lang not in lang_choice:
        try:
            text = translate.translate_text(Text=text, SourceLanguageCode='auto', TargetLanguageCode='en')['TranslatedText']
            lang = 'en'
        except: #ignore DetectedLanguageLowConfidenceException error
            text_list.pop()
            lang_list.pop()
            location_list.pop()
            continue
    
    # detect sentiment of tweet
    sentiment = comprehend.detect_sentiment(Text=text, LanguageCode=lang)['Sentiment']
    
    # add in lists
    sentiment_list.append(sentiment)

# define dataframe
df = pd.DataFrame({'lang':lang_list, 'sentiment':sentiment_list, 'location':location_list, 'tweet':text_list}).set_index(['sentiment','lang']).sort_index()
print(df.head())

# get counts per language for each sentiment
summary = df.groupby(level=[0,1]).size()

# bar plot
summary.unstack().plot(kind='bar')
plt.show()
print(summary)
        
print('Complete!')
