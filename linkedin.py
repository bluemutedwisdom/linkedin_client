#!/usr/bin/python

from __future__ import print_function
from BeautifulSoup import BeautifulSoup
import json
from pprint import pprint
import sys, getopt
import re
import requests, requests.utils, pickle
from html2text import html2text
import urllib
import os
from urlparse import parse_qs, parse_qsl, urlparse
import glob
import HTMLParser
import time
import getpass

html_parser = HTMLParser.HTMLParser()

def unescape(a):
    return html_parser.unescape(a).replace('&dsh; ', '-')

def filename(a):
    return re.sub(r'[ /?=&]+', '_', a)

host = 'https://www.linkedin.com/'
reload(sys)
sys.setdefaultencoding('utf-8')

class linkedin_client():
    def __init__(self):
        self.csrfToken = None
        self.bcookie = None
        self.rs = requests.Session()
        resp = None
        try:
            with open('linkedin-session') as f:
                self.rs.cookies  = requests.utils.cookiejar_from_dict(pickle.load(f))
        except:
            pass
        if not 'bcookie' in self.rs.cookies:
            self.linkedin_login();

    def linkedin_login(self):
        mail=os.environ.get('LINKEDIN_LOGIN')
        if mail is None:
            mail = os.environ.get('EMAIL');
        if mail is None:
            mail = raw_input('E-mail for linkedin login: ')
        pw = getpass.getpass('Password for ' + mail + ' on ' + host + ' >');
        self.rs.get(host);
        self.bcookie = re.search('.*v=2\&([^"]+)', self.rs.cookies['bcookie']).group(1)
        resp = self.rs.post(host + 'uas/login-submit',
                allow_redirects=False,
                headers = {'Content-Type': 'application/x-www-form-urlencoded' },
                data = {'session_key': mail, 'session_password': pw, 'loginCsrfParam': self.bcookie}
                )
        #print(resp.status_code)
        assert(resp.status_code == 302)
        resp = self.rs.get(host);
        open('login.html', 'w').write(resp.content)
        soup = BeautifulSoup(resp.content)
        identity = soup.find('code', { 'id': 'ozidentity-templates/identity-content'})
        if identity is None:
            print('Login failed');
            return
        with open('linkedin-session', 'w') as f:
            pickle.dump(requests.utils.dict_from_cookiejar(self.rs.cookies), f)
        data = json.loads(identity.getText())
        print('Welcome', data['member']['name']['firstName'])

    def identity(self):
        resp = self.rs.get(host);
        open('identity.html', 'w').write(resp.content)
        soup = BeautifulSoup(resp.content)
        identity = soup.find('code', { 'id': 'ozidentity-templates/identity-content'})
        identity2 = soup.find('code', { 'id': 'sharebox-static/templates/share-content'})
        self.id = json.loads(identity2.getText())['memberInfo']['id'];
        pprint(json.loads(identity2.getText())['memberInfo']['name']);
        #pprint(json.loads(identity.getText())['member'])
        #pprint(soup);
        if self.csrfToken is None:
            self.csrfToken = json.loads(soup.find('code', { 'id': '__pageContext__'}).getText())['csrfToken']
        return json.loads(identity.getText())['member']['name']['firstName']

    def inbox(self):
        resp = self.rs.get(host + 'messaging', headers = {'csrf-token': self.csrfToken });
        if resp.status_code != 200:
            print(resp)
        soup = BeautifulSoup(resp.content)
        for c in soup.findAll('code', id='inbox-main-content'):
            inbox = json.loads(c.getText())
            fn='inbox.json'
            open(fn, 'w').write(json.dumps(inbox, indent=4, sort_keys=True))
            for c in inbox['conversations']['conversationsBefore']:
                #print('Conversation: ', unescape(c['subject']));
                fn = filename(unescape(c['subject'])) + '.json'
                print(fn)
                open(fn, 'w').write(json.dumps(c, indent=4, sort_keys=True))
                continue # don't separate message
                for m in c['messages']:
                    s = m['sender']
                    #print(time.strftime('%c', time.localtime(int(m['timestamp'])/1000)), unescape(s['firstName']), unescape(s['lastName']) + ', ', unescape(m['subject']));
                    #print('From:', unescape(s['firstName']), unescape(s['lastName']) + ', ', unescape(s['headline']));
                    # 'recipients'
                    #print('Date: ', time.strftime('%c', time.localtime(int(m['timestamp'])/1000)))
                    #print('Subject: ', unescape(m['subject']));
                    #print('Read: ', unescape(str(m['read'])));
                    #print('\n' + unescape(str(m['body'])) + '\n\n')
                    fn = filename(unescape(s['firstName']) + ' ' +  unescape(s['lastName']) + ', ' + unescape(m['subject'])) + '.json'
                    print(fn)
                    open(fn, 'w').write(json.dumps(m, indent=4, sort_keys=True))

    def groups(self):
        resp = self.rs.get(host + 'communities-api/v1/communities/memberships/' + self.id + '?' +
                #+ '?projection=FULL&sortBy=RECENTLY_JOINED',
                '&count=500',
                headers = {'csrf-token': self.csrfToken });
        try:
            data = json.loads(resp.content)
            #pprint(data);
            for g in data['data']:
                #print(d['group']['id'] + '\t' +d['group']['mini']['name'])
                fn = filename(g['group']['mini']['name']) + '.json'
                print(fn)
                open(fn, 'w').write(json.dumps(g, indent=4, sort_keys=True))
            #pprint(g['group'])
        except (ValueError):
            raise(Exception(resp.content))

if __name__ == "__main__":
    li = linkedin_client();
    li.inbox()
    li.identity()
    print(li.id)
    li.groups()
