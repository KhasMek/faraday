import json
import logging
import socket
import urllib

from requests.adapters import ConnectionError, ReadTimeout

logger = logging.getLogger('Faraday searcher')


class ApiError(Exception):
    def __init__(self, message):
        super(ApiError, self).__init__(message)


class Structure:
    def __init__(self, **entries):
        self.__dict__.update(entries)

    @property
    def id(self):
        if hasattr(self, '_id'):
            return self._id
        return None

    @property
    def class_signature(self):
        if hasattr(self, 'type'):
            return self.type
        return None

    @property
    def parent_id(self):
        if hasattr(self, 'parent'):
            return self.parent
        return None

    def getMetadata(self):
        if hasattr(self, 'metadata'):
            return self.metadata
        return None


class Api:
    def __init__(self, workspace, requests=None, session=None, username=None, password=None,
                 base='http://127.0.0.1:5985/_api/', token=None):
        self.requests = requests
        self.workspace = workspace
        self.command_id = None  # Faraday uses this to tracker searcher changes.
        self.base = base
        if not self.base.endswith('/'):
            self.base += '/'
        self.token = token
        if not self.token and username and password:
            self.headers, self.cookies = self.login(username, password)
            if self.headers is None:
                raise UserWarning('Invalid username or password')

    def _url(self, path, is_get=False):
        url = self.base + 'v2/' + path
        if self.command_id and 'commands' not in url and not url.endswith('}') and not is_get:
            if '?' in url:
                url += '&command_id={}'.format(self.command_id)
            elif url.endswith('/'):
                url += '?command_id={}'.format(self.command_id)
            else:
                url += '/?command_id={}'.format(self.command_id)
        return url

    def _get(self, url, object_name):
        logger.debug('Getting url {}'.format(url))
        if self.headers:
            response = self.requests.get(url, headers=self.headers)
        else:
            response = self.requests.get(url, cookies=self.cookies)
        if response.status_code == 401:
            raise ApiError('Unauthorized operation trying to get {}'.format(object_name))
        if response.status_code != 200:
            raise ApiError('Cannot fetch {}'.format(object_name))
        if isinstance(response.json, dict):
            return response.json
        return json.loads(response.content)

    def _post(self, url, data, object_name):
        if self.headers:
            response = self.requests.post(url, json=data, headers=self.headers)
        else:
            response = self.requests.post(url, json=data, cookies=self.cookies)
        if response.status_code == 401:
            raise ApiError('Unauthorized operation trying to get {}'.format(object_name))
        if response.status_code != 201:
            raise ApiError('Cannot fetch {}, api response: {}'.format(object_name, getattr(response, 'text', None)))
        if isinstance(response.json, dict):
            return response.json
        return json.loads(response.content)

    def _put(self, url, data, object_name):
        if self.headers:
            response = self.requests.put(url, json=data, headers=self.headers)
        else:
            response = self.requests.put(url, json=data, cookies=self.cookies)
        if response.status_code == 401:
            raise ApiError('Unauthorized operation trying to upFdate {}'.format(object_name))
        if response.status_code != 200:
            raise ApiError('Unable to update {}'.format(object_name))
        if isinstance(response.json, dict):
            return response.json
        return json.loads(response.content)

    def _delete(self, url, object_name):
        if self.headers:
            response = self.requests.delete(url, headers=self.headers)
        else:
            response = self.requests.delete(url, cookies=self.cookies)
        if response.status_code == 401:
            raise ApiError('Unauthorized operation trying to delete {}'.format(object_name))
        if response.status_code != 204:
            raise ApiError('Unable to delete {}'.format(object_name))
        return True

    def login(self, username, password):
        auth = {"email": username, "password": password}
        try:
            resp = self.requests.post(self.base + 'login', json=auth)
            if resp.status_code not in [200, 302]:
                logger.info("Invalid credentials")
                return None
            else:
                cookies = getattr(resp, 'cookies', None)
                if cookies is not None:
                    token_response = self.requests.get(self.base + 'v2/token/', cookies=cookies)
                    if token_response.status_code != 404:
                        token = token_response.json()
                else:
                    token = self.requests.get(self.base + 'v2/token/').json

                header = {'Authorization': 'Token {}'.format(token)}

                return header, cookies
        except ConnectionError as ex:
            logger.exception(ex)
            logger.info("Connection error to the faraday server")
            return None
        except ReadTimeout:
            return None

    def create_command(self, itime, params, tool_name):
        self.itime = itime
        self.params = params
        self.tool_name = tool_name
        data = self._command_info()
        res = self._post(self._url('ws/{}/commands/'.format(self.workspace)), data, 'command')
        return res["_id"]

    def _command_info(self, duration=None):
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            ip = socket.gethostname()
        data = {
            "itime": self.itime,
            "command": self.tool_name,
            "ip": ip,
            "import_source": "shell",
            "tool": "Searcher",
            "params": json.dumps(self.params),
        }
        if duration:
            data.update({"duration": duration})
        return data

    def close_command(self, command_id, duration):
        data = self._command_info(duration)
        self._put(self._url('ws/{}/commands/{}/'.format(self.workspace, command_id)), data, 'command')

    def fetch_vulnerabilities(self):
        return [Structure(**item['value']) for item in self._get(self._url('ws/{}/vulns/'.format(self.workspace), True),
                                                                 'vulnerabilities')['vulnerabilities']]

    def fetch_services(self):
        return [Structure(**item['value']) for item in self._get(self._url('ws/{}/services/'.format(self.workspace), True),
                                                                 'services')['services']]

    def fetch_hosts(self):
        return [Structure(**item['value']) for item in self._get(self._url('ws/{}/hosts/'.format(self.workspace), True),
                                                                 'hosts')['rows']]

    def fetch_templates(self):
        return [Structure(**item['doc']) for item in
                self._get(self._url('vulnerability_template/', True), 'templates')['rows']]

    def filter_vulnerabilities(self, **kwargs):
        if len(kwargs.keys()) > 1:
            params = urllib.urlencode(kwargs)
            url = self._url('ws/{}/vulns/?{}'.format(self.workspace, params))
        else:
            params = self.parse_args(**kwargs)
            url = self._url('ws/{}/vulns/{}'.format(self.workspace, params), True)
        return [Structure(**item['value']) for item in
                self._get(url, 'vulnerabilities')['vulnerabilities']]

    def filter_services(self, **kwargs):
        params = urllib.urlencode(kwargs)
        url = self._url('ws/{}/services/?{}'.format(self.workspace, params), True)
        return [Structure(**item['value']) for item in
                self._get(url, 'services')['services']]

    def filter_hosts(self, **kwargs):
        params = urllib.urlencode(kwargs)
        url = self._url('ws/{}/hosts/?{}'.format(self.workspace, params), True)
        return [Structure(**item['value']) for item in
                self._get(url, 'hosts')['rows']]

    def filter_templates(self, **kwargs):
        templates = self.fetch_templates()
        filtered_templates = []
        for key, value in kwargs.items():
            for template in templates:
                if hasattr(template, key) and \
                        (getattr(template, key, None) == value or str(getattr(template, key, None)) == value):
                    filtered_templates.append(template)
        return filtered_templates

    def update_vulnerability(self, vulnerability):
        return Structure(**self._put(self._url('ws/{}/vulns/{}/'.format(self.workspace, vulnerability.id)),
                                     vulnerability.__dict__, 'vulnerability'))

    def update_service(self, service):
        if isinstance(service.ports, int):
            service.ports = [service.ports]
        else:
            service.ports = []
        return Structure(**self._put(self._url('ws/{}/services/{}/'.format(self.workspace, service.id)),
                                     service.__dict__, 'service'))

    def update_host(self, host):
        return Structure(**self._put(self._url('ws/{}/hosts/{}/'.format(self.workspace, host.id)),
                                     host.__dict__, 'hosts'))

    def delete_vulnerability(self, vulnerability_id):
        return self._delete(self._url('ws/{}/vulns/{}/'.format(self.workspace, vulnerability_id)), 'vulnerability')

    def delete_service(self, service_id):
        return self._delete(self._url('ws/{}/services/{}/'.format(self.workspace, service_id)), 'service')

    def delete_host(self, host_id):
        return self._delete(self._url('ws/{}/hosts/{}/'.format(self.workspace, host_id)), 'host')

    @staticmethod
    def parse_args(**kwargs):
        if len(kwargs.keys()) > 0:
            key = kwargs.keys()[0]
            value = kwargs.get(key, '')
            item = '"name":"{}","op":"eq","val":"{}"'.format(key, value)
            params = 'filter?q={"filters":[{' + item + '}]}'
            return params
        return ''

    @staticmethod
    def intersection(objects, models):
        return [_object for _object in objects if _object.id in [model.id for model in models]]

    @staticmethod
    def set_array(field, value, add=True, key=None, object=None):
        if isinstance(field, list):
            if add:
                if value not in field:
                    field.append(value)
            else:
                if value in field:
                    field.remove(value)
