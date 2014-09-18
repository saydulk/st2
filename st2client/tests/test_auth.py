import os
import sys
import uuid
import json
import mock
import tempfile
import requests
import argparse
import logging
import unittest2

from tests import base
from st2client import shell
from st2client.commands.resource import add_auth_token_to_kwargs
from st2client.utils.httpclient import add_auth_token_to_headers, add_json_content_type_to_headers


LOG = logging.getLogger(__name__)

RULE = {
    'id': uuid.uuid4().hex,
    'name': 'drule',
    'description': 'i am THE rule.'
}


class TestAuthToken(unittest2.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestAuthToken, self).__init__(*args, **kwargs)
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument('-t', '--token', dest='token')
        self.shell = shell.Shell()

    def setUp(self):
        # Setup environment.
        os.environ['ST2_BASE_URL'] = 'http://localhost'
        if 'ST2_AUTH_TOKEN' in os.environ:
            del os.environ['ST2_AUTH_TOKEN']

        # Redirect standard output and error to null. If not, then
        # some of the print output from shell commands will pollute
        # the test output.
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')

    def tearDown(self):
        # Clean up environment.
        if 'ST2_AUTH_TOKEN' in os.environ:
            del os.environ['ST2_AUTH_TOKEN']
        if 'ST2_BASE_URL' in os.environ:
            del os.environ['ST2_BASE_URL']

        # Reset to original stdout and stderr.
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    @add_auth_token_to_kwargs
    def _mock_run(self, args, **kwargs):
        return kwargs

    def test_decorate_auth_token_by_cli(self):
        token = uuid.uuid4().hex
        args = self.parser.parse_args(args=['-t', token])
        self.assertDictEqual(self._mock_run(args), {'token': token})
        args = self.parser.parse_args(args=['--token', token])
        self.assertDictEqual(self._mock_run(args), {'token': token})

    def test_decorate_auth_token_by_env(self):
        token = uuid.uuid4().hex
        os.environ['ST2_AUTH_TOKEN'] = token
        args = self.parser.parse_args(args=[])
        self.assertDictEqual(self._mock_run(args), {'token': token})

    def test_decorate_without_auth_token(self):
        args = self.parser.parse_args(args=[])
        self.assertDictEqual(self._mock_run(args), {})

    @add_auth_token_to_headers
    @add_json_content_type_to_headers
    def _mock_http(self, url, **kwargs):
        return kwargs

    def test_decorate_auth_token_to_http_headers(self):
        token = uuid.uuid4().hex
        kwargs = self._mock_http('/', token=token)
        expected = {'content-type': 'application/json', 'X-Auth-Token': token}
        self.assertIn('headers', kwargs)
        self.assertDictEqual(kwargs['headers'], expected)

    def test_decorate_without_auth_token_to_http_headers(self):
        kwargs = self._mock_http('/', auth=('stanley', 'stanley'))
        expected = {'content-type': 'application/json'}
        self.assertIn('auth', kwargs)
        self.assertEqual(kwargs['auth'], ('stanley', 'stanley'))
        self.assertIn('headers', kwargs)
        self.assertDictEqual(kwargs['headers'], expected)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps({}), 200, 'OK')))
    def test_decorate_resource_list(self):
        url = 'http://localhost:9101/rules'

        # Test without token.
        self.shell.run(['rule', 'list'])
        kwargs = {}
        requests.get.assert_called_with(url, **kwargs)

        # Test with token.
        token = uuid.uuid4().hex
        self.shell.run(['rule', 'list', '-t', token])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(url, **kwargs)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps([RULE]), 200, 'OK')))
    def test_decorate_resource_get(self):
        url = 'http://localhost:9101/rules/?name=%s' % RULE['name']

        # Test without token.
        self.shell.run(['rule', 'get', RULE['name']])
        kwargs = {}
        requests.get.assert_called_with(url, **kwargs)

        # Test with token.
        token = uuid.uuid4().hex
        self.shell.run(['rule', 'get', RULE['name'], '-t', token])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(url, **kwargs)

    @mock.patch.object(
        requests, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(RULE), 200, 'OK')))
    def test_decorate_resource_post(self):
        url = 'http://localhost:9101/rules'
        data = {'name': RULE['name'], 'description': RULE['description']}

        fd, path = tempfile.mkstemp()
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(data, indent=4))

            # Test without token.
            self.shell.run(['rule', 'create', path])
            kwargs = {'headers': {'content-type': 'application/json'}}
            requests.post.assert_called_with(url, json.dumps(data), **kwargs)

            # Test with token.
            token = uuid.uuid4().hex
            self.shell.run(['rule', 'create', path, '-t', token])
            kwargs = {'headers': {'content-type': 'application/json', 'X-Auth-Token': token}}
            requests.post.assert_called_with(url, json.dumps(data), **kwargs)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps([RULE]), 200, 'OK')))
    @mock.patch.object(
        requests, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(RULE), 200, 'OK')))
    def test_decorate_resource_put(self):
        get_url = 'http://localhost:9101/rules/?name=%s' % RULE['name']
        put_url = 'http://localhost:9101/rules/%s' % RULE['id']
        data = {'name': RULE['name'], 'description': RULE['description']}

        fd, path = tempfile.mkstemp()
        try:
            with open(path, 'a') as f:
                f.write(json.dumps(data, indent=4))

            # Test without token.
            self.shell.run(['rule', 'update', RULE['name'], path])
            kwargs = {}
            requests.get.assert_called_with(get_url, **kwargs)
            kwargs = {'headers': {'content-type': 'application/json'}}
            requests.put.assert_called_with(put_url, json.dumps(RULE), **kwargs)

            # Test with token.
            token = uuid.uuid4().hex
            self.shell.run(['rule', 'update', RULE['name'], path, '-t', token])
            kwargs = {'headers': {'X-Auth-Token': token}}
            requests.get.assert_called_with(get_url, **kwargs)
            kwargs = {'headers': {'content-type': 'application/json', 'X-Auth-Token': token}}
            requests.put.assert_called_with(put_url, json.dumps(RULE), **kwargs)
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps([RULE]), 200, 'OK')))
    @mock.patch.object(
        requests, 'delete',
        mock.MagicMock(return_value=base.FakeResponse('', 204, 'OK')))
    def test_decorate_resource_delete(self):
        get_url = 'http://localhost:9101/rules/?name=%s' % RULE['name']
        del_url = 'http://localhost:9101/rules/%s' % RULE['id']

        # Test without token.
        self.shell.run(['rule', 'delete', RULE['name']])
        kwargs = {}
        requests.get.assert_called_with(get_url, **kwargs)
        requests.delete.assert_called_with(del_url, **kwargs)

        # Test with token.
        token = uuid.uuid4().hex
        self.shell.run(['rule', 'delete', RULE['name'], '-t', token])
        kwargs = {'headers': {'X-Auth-Token': token}}
        requests.get.assert_called_with(get_url, **kwargs)
        requests.delete.assert_called_with(del_url, **kwargs)