# -*- coding: utf-8 -*-
import json, re, datetime
import pymongo
import wikitools
from config import config

class API:
	def __init__(self, wiki_api_url, username, password):
		self.wiki = wikitools.Wiki(wiki_api_url)
		self.wiki.login(username=username, password=password)
		self.dateRE = re.compile(r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z')

	def get_date_from_string(self, date_string):
		res = self.dateRE.search(date_string)
		year = int(res.group(1))
		month = int(res.group(2))
		day = int(res.group(3))
		hour = int(res.group(4))
		minute = int(res.group(5))
		second = int(res.group(6))
		d = datetime.datetime(year, month, day, hour, minute, second)
		date_index_string = '{0}-{1}-{2}'.format(year, month, day)

		return d, date_index_string

	def get_users(self, edited_only=False):
		params = {'action': 'query',
                  'list': 'allusers',
                  'aulimit': '5000',
                  'auprop': 'registration'
                  }

		if edited_only:
			params['auwitheditsonly'] = ''

		req = wikitools.api.APIRequest(self.wiki, params)
		res = req.query(querycontinue=True)

		return res['query']['allusers']

	def get_user_edits(self, user, start=None):
		params = {'action': 'query',
                  'list': 'usercontribs',
                  'ucuser': user,
                  'uclimit': '5000'
                  }

		if start:
			params['ucend'] = start
			params['ucstart'] = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

		req = wikitools.api.APIRequest(self.wiki, params)
		res = req.query(querycontinue=True)

		return res['query']['usercontribs']

	def get_recent_changes(self, start=None):
		params = {'action': 'query',
                  'list': 'recentchanges',
                  'rcprop': 'user|timestamp|title|ids',
                  'rctype': 'edit|new',
                  'rcdir': 'newer',
                  'rclimit': '5000'
                  }

		if start:
			params['rcstart'] = start

		req = wikitools.api.APIRequest(self.wiki, params)
		res = req.query(querycontinue=True)

		return res['query']['recentchanges']
