# -*- coding: utf-8 -*-
import json
import pymongo
from flask import Flask, url_for, render_template, request, Response
import analyze
from config import config
from werkzeug.contrib.cache import MemcachedCache

app = Flask(__name__)
cache = MemcachedCache(['{0}:{1}'.format(config['memcached']['host'], config['memcached']['port'])])
connection = pymongo.Connection(config['db']['host'], config['db']['port'])

wiki_dict = {}
for wiki in config['wikis']:
	db = connection[config['wikis'][wiki]['db_name']]
	print('Successfully loaded ' + wiki)
	wiki_dict[wiki] = db


def get_user_chart_data(wiki, db, user):
	charts_data = cache.get('wiki-fi:userdata_{0}_{1}'.format(user['username'].replace(' ', '_'), wiki))
	if charts_data is None:
		charts_data = analyze.analyze_user(wiki, db, user)
		cache.set('wiki-fi:userdata_{0}_{1}'.format(user['username'].replace(' ', '_'), wiki), charts_data, timeout=0)
	return charts_data

def get_page_chart_data(wiki, db, page):
	charts_data = cache.get('wiki-fi:pagedata_{0}_{1}'.format(page['title'].replace(' ', '_'), wiki))
	if charts_data is None:
		charts_data = analyze.analyze_page(wiki, db, page)
		cache.set('wiki-fi:pagedata_{0}_{1}'.format(page['title'].replace(' ', '_'), wiki), charts_data, timeout=0)
	return charts_data

def get_wiki_chart_data(wiki, db):
	charts_data = cache.get('wiki-data_{0}'.format(wiki))
	if charts_data is None:
		charts_data = analyze.analyze_wiki(wiki, db)
		cache.set('wiki-data_{0}'.format(wiki), charts_data, timeout=0)
	return charts_data

@app.route('/is_valid_user', methods=['POST'])
def is_valid_user():
	username = request.form['username']
	wiki = request.form['wiki']
	wikiuserlist = cache.get('wiki-fi:userlist_{0}'.format(wiki))
	if wikiuserlist is None:
		wikiuserlist = [user['username'] for user in wiki_dict[wiki]['users'].find(fields=['username'])]
		cache.set('wiki-fi:userlist_{0}'.format(wiki), wikiuserlist, timeout=0)
	data = username in wikiuserlist
	resp = Response(json.dumps(data), status=200, mimetype='application/json')

	return resp

@app.route('/get_all_users', methods=['GET'])
def get_all_users():
	users = cache.get('wiki-fi:allusers')
	if users is None:
		users = []
		for wiki in config['wikis']:
			users += [user['username'] for user in wiki_dict[wiki]['users'].find(fields=['username'])]
		users = list(set(users))
		cache.set('wiki-fi:allusers', users, timeout=0)
	resp = Response(json.dumps(users), status=200, mimetype='application/json')

	return resp

@app.route('/get_wiki_users', methods=['POST'])
def get_wiki_users():
	wiki = request.form['wiki']
	wikiuserlist = cache.get('wiki-fi:userlist_{0}'.format(wiki))
	if wikiuserlist is None:
		wikiuserlist = [user['username'] for user in wiki_dict[wiki]['users'].find(fields=['username'])]
		cache.set('wiki-fi:userlist_{0}'.format(wiki), wikiuserlist, timeout=0)
	resp = Response(json.dumps(wikiuserlist), status=200, mimetype='application/json')

	return resp

@app.route('/get_user_wikis', methods=['POST'])
def get_user_wikis():
	username = request.form['username']
	userwikislist = cache.get('wiki-fi:userwikislist_{0}'.format(username.replace(' ', '_')))
	if userwikislist is None:
		userwikislist = []
		for wiki in wiki_dict:
			if wiki_dict[wiki]['users'].find_one({'username': username}, fields=[]):
				userwikislist.append(wiki)
		cache.set('wiki-fi:userwikislist_{0}'.format(username.replace(' ', '_')), userwikislist, timeout=0)
	resp = Response(json.dumps(userwikislist), status=200, mimetype='application/json')

	return resp

@app.route('/get_last_updated', methods=['POST'])
def get_last_updated():
	wiki = request.form['wiki']
	last_updated = cache.get('wiki-fi:wiki_last_updated_' + wiki)
	if last_updated is None:
		last_updated = (wiki_dict[wiki]['metadata'].find_one({'key': 'last_updated'}, fields=['last_updated']))['last_updated']
		cache.set('wiki-fi:wiki_last_updated_' + wiki, last_updated, timeout=0)
	last_updated = last_updated.strftime("%H:%M, %d %B %Y (UTC)")
	resp = Response(json.dumps(last_updated), status=200, mimetype='application/json')

	return resp

@app.route('/')
def homepage():
	return render_template('form.html')

def invalid_args(error):
	return render_template('form.html', error=error)

@app.route('/about')
def about():
	return render_template('about.html')

@app.route('/user', methods=['GET'])
def anaylze_user():
	if 'username' not in request.args:
		return invalid_args(error="invalid username")
	if 'wiki' not in request.args or request.args['wiki'] not in wiki_dict:
		return invalid_args(error="invalid wiki")

	username = request.args['username']
	wiki = request.args['wiki']
	user = wiki_dict[wiki]['users'].find_one({'username': username})
	if user is None:
		return invalid_args(error="invalid username")
	wiki_link = config['wikis'][wiki]['wiki_link']

	charts_data = get_user_chart_data(wiki, wiki_dict[wiki], user)

	return render_template('user_stats.html', username=username, wiki=wiki, wiki_link=wiki_link, charts_data=charts_data)

@app.route('/page', methods=['GET'])
def anaylze_page():
	if 'page' not in request.args:
		return invalid_args('invalid page')
	if 'wiki' not in request.args or request.args['wiki'] not in wiki_dict:
		return invalid_args('invalid wiki')

	page = request.args['page']
	wiki = request.args['wiki']
	page = wiki_dict[wiki]['pages'].find_one({'title': page})
	if page is None:
		return invalid_args('invalid page')
	wiki_link = config['wikis'][wiki]['wiki_link']

	charts_data = get_page_chart_data(wiki, wiki_dict[wiki], page)

	return render_template('page_stats.html', page_name=page['title'], wiki=wiki, wiki_link=wiki_link, charts_data=charts_data)

@app.route('/wiki', methods=['GET'])
def anaylze_wiki():
	if request.args['wiki'] not in wiki_dict:
		return invalid_args('invalid wiki')

	wiki = request.args['wiki']
	wiki_link = config['wikis'][wiki]['wiki_link']
	charts_data = get_wiki_chart_data(wiki, wiki_dict[wiki])

	return render_template('wiki_stats.html', wiki_name=config['wikis'][wiki]['wiki_name'], wiki=wiki, wiki_link=wiki_link, charts_data=charts_data)

if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0', port=5000)
