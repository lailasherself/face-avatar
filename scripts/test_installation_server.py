"""HTTP cache regression tests; no browser or physical camera required."""
from functools import partial
from contextlib import closing
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch

from run_installation import Handler, installation_version


class QuietHandler(Handler):
    def log_message(self,*args):pass


class InstallationServerTests(unittest.TestCase):
    def setUp(self):
        self.directory=TemporaryDirectory()
        root=Path(self.directory.name)
        for name in ['cockpit.html','fleet.js','fleet.css','model.glb','worker.js']:
            (root/name).write_text('current '+name)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(root)))
        self.thread=Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        self.directory.cleanup()

    def request(self,path,headers=None,method='GET'):
        with closing(HTTPConnection('127.0.0.1',self.server.server_port)) as connection:
            connection.request(method,path,headers=headers or {})
            response=connection.getresponse()
            return response.status,dict(response.getheaders()),response.read()

    def test_root_redirects_to_current_installation_preserving_options(self):
        status,headers,_=self.request('/?setup&character=pearl')
        self.assertEqual(status,302)
        self.assertEqual(headers['Location'],'/cockpit.html?setup&character=pearl')
        self.assertIn('no-store',headers['Cache-Control'])

    def test_disconnected_logging_does_not_abort_http_responses(self):
        for error in [BrokenPipeError('disconnected launcher'),ValueError('closed stream')]:
            with patch.object(QuietHandler,'log_message',Handler.log_message),patch('sys.stderr') as stderr:
                stderr.write.side_effect=error
                status,_,body=self.request('/fleet.js')
                self.assertEqual(status,200)
                self.assertEqual(body,b'current fleet.js')

    def test_all_runtime_files_disable_caching(self):
        for path in ['/cockpit.html','/fleet.js','/fleet.css','/model.glb','/worker.js']:
            version=installation_version(self.directory.name)
            status,headers,body=self.request('/_build/'+version+path)
            self.assertEqual(status,200)
            self.assertIn('no-store',headers['Cache-Control'])
            self.assertEqual(body.decode(),'current '+path[1:])

    def test_conditional_requests_cannot_keep_stale_content(self):
        for method in ['GET','HEAD']:
            status,headers,_=self.request('/fleet.js',{
                'If-Modified-Since':'Fri, 01 Jan 2100 00:00:00 GMT','If-None-Match':'"old"',
            },method)
            self.assertEqual(status,200)
            self.assertIn('no-store',headers['Cache-Control'])

    def test_explicit_refresh_clears_cache_not_user_data(self):
        _,headers,_=self.request('/cockpit.html?refresh=arms-v3')
        self.assertEqual(headers['Clear-Site-Data'],'"cache"')
        for path in ['/cockpit.html','/fleet.js?refresh=arms-v3']:
            _,headers,_=self.request(path)
            self.assertNotIn('Clear-Site-Data',headers)

    def test_stale_build_redirects_to_new_version_with_options(self):
        before=installation_version(self.directory.name)
        (Path(self.directory.name)/'fleet.js').write_text('updated arm controls')
        after=installation_version(self.directory.name)
        self.assertNotEqual(before,after)
        status,headers,_=self.request(f'/_build/{before}/cockpit.html?setup&character=pearl')
        self.assertEqual(status,302)
        self.assertEqual(headers['Location'],f'/_build/{after}/cockpit.html?setup&character=pearl')

    def test_canonical_page_versions_entire_relative_module_graph(self):
        status,headers,_=self.request('/cockpit.html')
        self.assertEqual(status,302)
        location=headers['Location']
        self.assertTrue(location.startswith('/_build/'))
        status,_,body=self.request(location.replace('cockpit.html','worker.js'))
        self.assertEqual(status,200)
        self.assertEqual(body,b'current worker.js')


if __name__=='__main__':unittest.main()
