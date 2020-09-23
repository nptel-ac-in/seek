# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import Cookie
import logging
import os

def get_cookie_value(key):
    cookies = None
    try:
        cookies = Cookie.BaseCookie(os.environ.get('HTTP_COOKIE',''))
    except Cookie.CookieError, error:
        logging.debug("Ignoring Cookie Error, skipping get cookie: '%s'" % error)

    if not cookies:
        return None

    cookie = cookies.get(key)

    if not cookie:
        return None

    return cookie.value

# Cookie handling from http://appengine-cookbook.appspot.com/recipe/a-simple-cookie-class/
def set_cookie_value(key, value='', max_age=None,
               path='/', domain=None, secure=None, httponly=False,
               version=None, comment=None):
    cookies = Cookie.BaseCookie()
    cookies[key] = value
    for var_name, var_value in [
        ('max-age', max_age),
        ('path', path),
        ('domain', domain),
        ('secure', secure),
        #('HttpOnly', httponly), Python 2.6 is required for httponly cookies
        ('version', version),
        ('comment', comment),
        ]:
        if var_value is not None and var_value is not False:
            cookies[key][var_name] = str(var_value)
        if max_age is not None:
            cookies[key]['expires'] = max_age

    cookies_header = cookies[key].output(header='').lstrip()

    if httponly:
        # We have to manually add this part of the header until GAE uses Python 2.6.
        cookies_header += "; HttpOnly"

    return cookies_header


