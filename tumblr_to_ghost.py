import time
import math
import re

import requests
import pandoc


API_URL = "http://api.tumblr.com/v2/blog/{url}/{resource}?api_key={api_key}"

class TumblrInfoResponseError(Exception):
    pass

class TumblrToGhost(object):
    def __init__(self, api_key, tumblr_blog_url):
        self.api_key = api_key
        self.tumblr_blog_url = tumblr_blog_url
        self.api_url = API_URL.format(
            url='{url}',
            resource='{resource}',
            api_key=self.api_key
        )

    def get_blog_info(self):
        url = self.api_url.format(url=self.tumblr_blog_url, resource='info')
        r = requests.get(url)
        return r.json()

    def get_posts(self):
        try:
            blog_info = self.get_blog_info()['response']['blog']
        except TypeError:
            raise TumblrInfoResponseError(
                'Make sure this is a valid Tumblr blog URL.'
            )

        post_count = blog_info['posts']
        offset = 0
        limit = 20
        steps = post_count / limit
        posts = []

        if post_count % limit != 0:
            steps = int(math.floor(steps) + 1)

        for step in range(0, steps):
            url_template = '{}{}'.format(self.api_url,
                                         '&offset={offset}&limit={limit}')
            url = url_template.format(url=self.tumblr_blog_url,
                                      resource='posts',
                                      offset=offset, limit=limit)

            r = requests.get(url)
            posts.extend(r.json()['response']['posts'])

            offset += limit

        return self.create_ghost_export(posts)

    def create_ghost_export(self, posts):
        ghost_posts = []
        tumblr_tags = []

        for post in posts:
            doc = pandoc.Document()

            body = self.create_body(post)

            doc.html = body.encode('ascii', 'ignore')

            tumblr_tags.extend(post['tags'])

            timestamp = post['timestamp'] * 1000

            ghost_posts.append({
                "title": self.create_title(post),
                "slug": post['slug'],
                "markdown": doc.markdown,
                "html": body,
                "image": None,
                "featured": 0,
                "page": 0,
                "status": "published",
                "language": "en_US",
                "meta_title": None,
                "meta_description": None,
                "author_id": 1,
                "created_at": timestamp,
                "created_by": 1,
                "updated_at": timestamp,
                "updated_by": 1,
                "published_at": timestamp,
                "published_by": 1
            })

        export_object = {
            "meta": {
                "exported_on": int(time.time()) * 1000,
                "version": "000"
            },
            "data": {
                "posts": ghost_posts,
                "tags": self.create_tags(set(tumblr_tags))
            }
        }

        return export_object

    def create_title(self, post):
        type = post['type']

        if type =='photo':
            if post['caption']:
                clean_tags = re.compile(r'<.*?>')
                title = clean_tags.sub('', post['caption'])
            else:
                title = 'Image'
        else:
            title = post['title']

        return title

    def create_body(self, post):
        type = post['type']

        if type == 'text':
            body = post['body']
        elif type == 'link':
            description = post['description'].encode('ascii', 'ignore')
            body = """
            <strong><a href="{}">{}</a></strong>
            <p>{}</p>
            """.format(post['url'], post['title'], description)
        elif type == 'photo':
            body = '<p>{}</p>'.format(post['caption'])

            for photo in post['photos']:
                body += '<p>{}</p><img src="{}">'.format(
                    photo['caption'], photo['original_size']['url'])

        return body

    def create_tags(self, tumblr_tags):
        ghost_tags = []

        for tag in tumblr_tags:
            now = int(time.time()) * 1000
            ghost_tags.append({
                "name": tag.title(),
                "slug": tag,
                "description": None,
                "parent_id": None,
                "meta_title": None,
                "meta_description": None,
                "created_at": now,
                "created_by": 1,
                "updated_at": now,
                "updated_by": 1
            })

        return ghost_tags
