"""Serve the bundled installation locally and open its dedicated kiosk browser."""
import argparse
import hashlib
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

ROOT=Path(__file__).resolve().parents[1]

def installation_version(root):
    root=Path(root)
    files=[p for p in root.iterdir() if p.is_file() and p.suffix in {'.html','.js','.mjs','.css','.json','.glb'}]
    for folder in ('assets','vendor','scripts'):
        if (root/folder).is_dir():files.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    digest=hashlib.sha256()
    for path in sorted(files):
        stat=path.stat()
        digest.update(f'{path.relative_to(root)}:{stat.st_size}:{stat.st_mtime_ns}\n'.encode())
    return digest.hexdigest()[:16]

def build_path(path):
    parts=urlsplit(path).path.split('/')
    if len(parts)>=4 and parts[1]=='_build' and len(parts[2])==16 and all(c in '0123456789abcdef' for c in parts[2]):
        return '/'+ '/'.join(parts[3:]),parts[2]
    return urlsplit(path).path,None

def find_browser(explicit=None):
    candidates=[explicit] if explicit else []
    if sys.platform=='win32':
        for base in ['PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA']:
            folder=os.environ.get(base,'')
            if folder:
                candidates.extend([str(Path(folder)/'Google/Chrome/Application/chrome.exe'),str(Path(folder)/'Microsoft/Edge/Application/msedge.exe')])
    elif sys.platform=='darwin':
        candidates.append('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    candidates.extend(['chromium','chromium-browser','google-chrome','google-chrome-stable','microsoft-edge'])
    for candidate in candidates:
        found=shutil.which(candidate)
        if found:return found
    raise RuntimeError('Install Chrome or Chromium, or pass --browser with its executable path.')

class Handler(SimpleHTTPRequestHandler):
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.mjs':'text/javascript','.wasm':'application/wasm','.glb':'model/gltf-binary'}
    def log_message(self,format,*args):
        # A detached launcher can lose stderr; logging must not abort responses.
        try:super().log_message(format,*args)
        except (OSError,ValueError):pass

    def send_head(self):
        if urlsplit(self.path).path.startswith('/api/zed/'):
            self.zed_request();return None
        request=urlsplit(self.path)
        if request.path=='/':
            self.send_response(302)
            self.send_header('Location',urlunsplit(('','','/cockpit.html',request.query,'')))
            self.send_header('Content-Length','0')
            self.end_headers()
            return None
        logical,version=build_path(self.path)
        if logical=='/cockpit.html':
            current=installation_version(self.directory)
            if version!=current:
                self.send_response(302)
                self.send_header('Location',urlunsplit(('','',f'/_build/{current}/cockpit.html',request.query,'')))
                self.send_header('Content-Length','0')
                self.end_headers()
                return None
        # Local files can change within HTTP Last-Modified's one-second resolution.
        # Always send current bytes rather than validating an older cached response.
        for name in ('If-Modified-Since','If-None-Match'):
            if name in self.headers:del self.headers[name]
        return super().send_head()

    def do_POST(self):
        if urlsplit(self.path).path.startswith('/api/zed/'):self.zed_request()
        else:self.send_error(404)

    def zed_request(self):
        host=self.headers.get('Host','')
        allowed={f'localhost:{self.server.server_port}',f'127.0.0.1:{self.server.server_port}'}
        origin=self.headers.get('Origin')
        if host not in allowed or self.headers.get('Sec-Fetch-Site') not in (None,'same-origin') or (origin and origin!='http://'+host):
            self.send_error(403,'ZED is restricted to this local installation');return
        if self.command=='POST' and self.headers.get('X-Face-Avatar')!='zed':
            self.send_error(403,'Missing installation request header');return
        capture=getattr(self.server,'zed_capture',None)
        if capture is None:self.send_error(503,'Start the launcher with --tracking zed');return
        try:
            path=urlsplit(self.path).path
            if self.command=='POST' and path=='/api/zed/start':capture.start();self.send_response(202)
            elif self.command=='POST' and path=='/api/zed/stop':capture.stop();self.send_response(204)
            elif self.command=='GET' and path=='/api/zed/frame':
                snapshot=capture.snapshot()
                if snapshot is None:self.send_response(204)
                else:
                    packet,jpeg=snapshot
                    self.send_response(200);self.send_header('Content-Type','image/jpeg')
                    self.send_header('X-Zed-Sample',json.dumps(packet,separators=(',',':'),allow_nan=False))
                    self.send_header('Content-Length',str(len(jpeg)));self.end_headers()
                    self.wfile.write(jpeg);return
            else:self.send_error(404);return
            self.send_header('Content-Length','0');self.end_headers()
        except RuntimeError as error:
            body=json.dumps({'error':str(error)}).encode()
            self.send_response(503);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)

    def translate_path(self,path):
        logical,_=build_path(path)
        return super().translate_path(logical)

    def end_headers(self):
        self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma','no-cache')
        self.send_header('Expires','0')
        request=urlsplit(self.path)
        if request.path.endswith('.html') and 'refresh' in parse_qs(request.query):
            # Cache only: preserve camera permissions, cookies, and saved user data.
            self.send_header('Clear-Site-Data','"cache"')
        super().end_headers()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8012)
    parser.add_argument('--browser')
    parser.add_argument('--setup',action='store_true',help='Open operator controls for initial camera permission and calibration')
    parser.add_argument('--assets',choices=['fleet','3dai'],default='3dai',help='Local character set (3dai contains source-based review rigs)')
    parser.add_argument('--tracking',choices=['webcam','zed'],default='webcam',help='Native ZED RGB/body input or preserved development webcam input')
    parser.add_argument('--zed-serial',type=int,help='Select a specific connected ZED camera')
    parser.add_argument('--serve-only',action='store_true',help='Serve current installation files without opening a browser')
    parser.add_argument('--check',action='store_true',help='Check prerequisites without starting the camera or browser')
    args=parser.parse_args()
    try:
        browser=None if args.serve_only else find_browser(args.browser)
        required=['cockpit.html','assets/fleet/manifest.json','vendor/mediapipe/model/face_landmarker.task','vendor/mediapipe/model/hand_landmarker.task','vendor/mediapipe/model/pose_landmarker_lite.task','air-swipe.js','hand-tracking-worker.js','arm-retarget.js','body-motion.js','eye-signals.js','eyelid-surface.js']
        if args.assets=='3dai':required.append('assets/3dai/manifest.json')
        required.extend(['finger-motion.js','finger-retarget.js','pose-correctives.js','post-skin-correctives.js','arm-collisions.js','vendor/rapier/rapier.mjs'])
        required.extend(['vendor/mediapipe/vision_pose_bundle.mjs',
                         'tongue-tracking.js','tongue-tracking-worker.js','tongue-model.js','tongue-signal.js',
                         'vendor/tongue/tongue_detector.onnx','vendor/onnxruntime/ort.wasm.min.mjs',
                         'vendor/onnxruntime/ort-wasm-simd-threaded.mjs','vendor/onnxruntime/ort-wasm-simd-threaded.wasm'])
        required.extend(['face-tracking.js','face-tracking-worker.js','finger-tracking-worker.js','hand-crops.js','camera-framing.js','mouth-signals.js','zed-source.js','zed-motion.js'])
        for name in required:
            if not (ROOT/name).is_file():raise RuntimeError('Missing installation file: '+name)
        capture=None
        if args.tracking=='zed':
            from zed_capture import ZedCapture,prerequisites
            prerequisites();capture=ZedCapture(args.zed_serial)
        if args.check:
            print('Ready. Browser: '+(browser or 'not required in serve-only mode'));print('Assets: '+str(ROOT));return
        options={'setup':'1'} if args.setup else {}
        options['assets']=args.assets
        options['tracking']=args.tracking
        if not args.serve_only:options['refresh']=str(time.time_ns())
        url=f'http://localhost:{args.port}/cockpit.html'+('?' + urlencode(options) if options else '')
        profile=Path.home()/'.face-avatar'/'browser-profile'
        handler=partial(Handler,directory=str(ROOT))
        with ThreadingHTTPServer(('127.0.0.1',args.port),handler) as server:
            server.zed_capture=capture
            if not args.serve_only:
                command=[browser,'--user-data-dir='+str(profile),'--no-first-run','--no-default-browser-check','--autoplay-policy=no-user-gesture-required']
                command.extend(['--new-window',url] if args.setup else ['--kiosk',url])
                subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            print('Face Avatar running at '+url,flush=True)
            try:server.serve_forever()
            except KeyboardInterrupt:pass
            finally:
                if capture:capture.stop()
    except (RuntimeError,OSError) as error:
        parser.exit(1,str(error)+'\n')

if __name__=='__main__':main()
