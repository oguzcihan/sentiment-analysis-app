from flask import *
from twython import Twython
import numpy as np
import pandas as pd
import re
import string
from flask_mysqldb import MySQL
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences
from keras.models import load_model
import datetime as dt

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

'''MYSQL CONFIG'''
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'dbTwitter'
mysql = MySQL(app)

'''Twython CONFIG'''
APP_KEY = 'gxGZNWC2MPB0hd94ZbcFxBIx0'
APP_SECRET = 'LhPhGPct9GZu1Ig8yKSUCiDuYXGtu5bBXXNeo34BSJA4hg2YNw'
twitter = Twython(APP_KEY, APP_SECRET, oauth_version=2)
ACCESS_TOKEN = twitter.obtain_access_token()
twitter = Twython(APP_KEY, access_token=ACCESS_TOKEN)

data = pd.read_csv('D:\PycharmProject\Twitter\static\TweetsText-2.csv')
# data = data[data['airline_sentiment'] != 'neutral']
#
#
# def clean_tweet(text):
#     tweet = ''
#     tweet = re.sub('[' + string.punctuation + ']', '', text)
#     tweet = re.sub(r"http\S+|www\S+|https\S+", '', text, flags=re.MULTILINE)
#     # Remove user @ references and '#' from tweet
#     tweet = re.sub(r'\@\w+|\#', '', text)
#     return tweet
#
#
# data['text'] = data['text'].apply(lambda x: clean_tweet(x))
#
# for idx, row in data.iterrows():
#     row[0] = row[0].replace('rt', '')

max_fatures = 5000
tokenizer = Tokenizer(num_words=max_fatures, split=' ')
tokenizer.fit_on_texts(data['text'].values)
X = tokenizer.texts_to_sequences(data['text'].values)
pad_sequences(X, maxlen=50)


class SentimentScore:
    def __init__(self, positive_tweets, negative_tweets, neutral_tweets):
        self.positive_tweets = positive_tweets
        self.negative_tweets = negative_tweets
        self.neutral_tweets = neutral_tweets

        self.neg = len(negative_tweets)
        self.pos = len(positive_tweets)
        self.neut = len(neutral_tweets)


@app.route('/')
def index():
    return render_template('main.html')


@app.route('/usertimeline', methods=['GET', 'POST'])
def usertimeline():
    try:
        if request.method == 'POST':
            user_name = request.form['user_name']
            tw_count = request.form['us_count']
            if user_name == '' or tw_count == '':
                flash("Fields cannot be empty...", "danger")
                return render_template('user_timeline.html')
            else:
                user_timeline = twitter.get_user_timeline(screen_name=user_name, lang='en', count=tw_count)
                return render_template('user_result.html', result=sentiment_analysis(user_timeline), name=user_name,
                                       count=tw_count)
        else:
            return render_template('user_timeline.html')
    except BaseException as ex:
        print(ex)


def sentiment(text):
    try:
        tweet = [text]
        tweet = tokenizer.texts_to_sequences(tweet)
        tweet = pad_sequences(tweet, maxlen=50, dtype='int32', value=0)
        model = load_model('D:\\PycharmProject\\Twitter\\static\\model-2.h5')
        sentiment = model.predict(tweet, batch_size=128, verbose=0)[0]
        if (np.argmax(sentiment) == 0):
            return 'neutral'

        elif (np.argmax(sentiment) == 1):
            return 'positive'
        else:
            return 'negative'

    except BaseException as ex:
        print(ex)


def sentiment_analysis(tweets):
    try:
        negative_tweets = []
        positive_tweets = []
        neutral_tweets = []
        for tweet in tweets:

            res = sentiment(tweet['text'])
            if res == 'negative':
                negative_tweets.append(tweet['text'])
            elif res == 'positive':
                positive_tweets.append(tweet['text'])
            else:
                neutral_tweets.append(tweet['text'])

        score = SentimentScore(positive_tweets, negative_tweets, neutral_tweets)
        return score

    except BaseException as ex:
        print(ex)


def search_analysis(tweets):
    try:
        negative_tweets = []
        positive_tweets = []
        neutral_tweets = []
        for tweet in tweets['statuses']:

            res = sentiment(tweet['text'])
            if res == 'negative':
                negative_tweets.append(tweet['text'])
            elif res == 'positive':
                positive_tweets.append(tweet['text'])
            else:
                neutral_tweets.append(tweet['text'])

        score = SentimentScore(positive_tweets, negative_tweets, neutral_tweets)

        tw_query = request.form['query']
        tw_count = request.form['q_count']
        search_date = dt.date.today()
        negative = score.neg
        positive = score.pos
        neutral = score.neut

        negative_score = int((negative * 100) / int(tw_count))
        positive_score = int((positive * 100) / int(tw_count))
        neutral_score = int((neutral * 100) / int(tw_count))

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO tbTwitter(searchKey,searchDate,countTweet,negativePer,positivePer,neutralPer) VALUES (%s, %s,%s,%s,%s,%s)",
            (tw_query, search_date, tw_count, negative_score, positive_score, neutral_score))
        mysql.connection.commit()
        cur.close()

        return score

    except BaseException as ex:
        print(ex)


@app.route('/searchtimeline', methods=["POST", "GET"])
def search_timeline():
    try:
        if request.method == "POST":

            tw_query = request.form['query']
            tw_count = request.form['q_count']
            if tw_query == '' or tw_count == '':
                flash("Fields cannot be empty...", "danger")
                return render_template('search_timeline.html')
            else:
                searchtimeline = twitter.search(q=tw_query, lang='en', count=tw_count)
                return render_template('search_result.html', result=search_analysis(searchtimeline), query=tw_query,
                                       q_count=tw_count)
        else:
            return render_template('search_timeline.html')

    except BaseException as ex:
        print(ex)


@app.route('/history')
def search_history():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM tbTwitter")
        data = cur.fetchall()

        return render_template('search_history.html', data=data)
    except BaseException as ex:
        print(ex)


@app.route('/delete_history/<string:id>', methods=['POST'])
def delete_history(id):

    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM tbTwitter WHERE id=%s", [id])
        mysql.connection.commit()
        cur.close()
        flash("History Deleted", "success")

        return redirect(url_for('search_history'))

    except BaseException as ex:
        print(ex)

if __name__ == '__main__':
    app.run(debug=True)
