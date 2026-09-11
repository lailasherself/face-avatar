"""Native boundary tests without opening a camera or requiring NVIDIA libraries."""
import json
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
from test_installation_server import InstallationServerTests
from zed_capture import PersonSelector,ZedCapture,body_packet,visitor_region


class CaptureTests(unittest.TestCase):
    def test_visitor_mask_keeps_extended_wrists_and_fingertip_margin(self):
        bounds=[(.4,.2),(.6,.2),(.6,.8),(.4,.8)]
        joints={'RIGHT_WRIST':{'image':[.93,.5],'confidence':.9},
                'RIGHT_ELBOW':{'image':[.75,.5],'confidence':.9}}
        x0,y0,x1,y1=visitor_region(bounds,joints,960,540)
        self.assertEqual(x1,960);self.assertLess(x0,384)
        self.assertLess(y0,270);self.assertGreater(y1,270)
        joints['RIGHT_WRIST']['confidence']=.2
        self.assertLess(visitor_region(bounds,joints,960,540)[2],900)

    def test_visitor_mask_handles_missing_invalid_and_offscreen_coordinates(self):
        self.assertIsNone(visitor_region([],{},960,540))
        self.assertIsNone(visitor_region([(float('nan'),0)],{'WRIST':{'image':[float('inf'),.5],'confidence':1}},960,540))
        self.assertEqual(visitor_region([(-.1,-.1),(1.1,1.1)],{},960,540),(0,0,960,540))

    def test_identity_survives_order_changes_and_short_occlusion(self):
        select=PersonSelector();a=NS(id=1,position=[0,0,-2]);b=NS(id=2,position=[1,0,-2])
        self.assertIs(select.choose([b,a],1),a)
        self.assertIs(select.choose([b,a],1.1),a)
        self.assertIsNone(select.choose([b],1.5))
        self.assertIs(select.choose([b],2),b)

    def test_packet_has_named_confidence_gated_coordinates_and_no_nan(self):
        names=[s+'_'+p for s in ['LEFT','RIGHT'] for p in ['SHOULDER','ELBOW','WRIST','HAND']]
        sdk=NS(BODY_34_PARTS=NS(**{name:NS(value=i) for i,name in enumerate(names)}))
        body=NS(id=4,keypoint=[[0,0,-2] for _ in names],keypoint_2d=[[320,240] for _ in names],keypoint_confidence=[90]*8)
        body.keypoint[0][0]=float('nan')
        result=body_packet(body,sdk,640,480)
        self.assertNotIn('LEFT_SHOULDER',result['joints']);json.dumps(result,allow_nan=False)
        self.assertEqual(result['joints']['RIGHT_WRIST']['image'],[.5,.5])
        self.assertEqual(result['joints']['RIGHT_WRIST']['confidence'],.9)

    def test_latest_snapshot_expires_and_stop_clears_camera_pixels(self):
        capture=ZedCapture();capture.latest=({'sequence':1},b'jpeg',time.monotonic()-.04)
        packet,pixels=capture.snapshot();self.assertGreaterEqual(packet['ageMs'],40)
        self.assertEqual(pixels,b'jpeg')
        capture.latest=({},b'old',time.monotonic()-1);self.assertIsNone(capture.snapshot())
        capture.stop();self.assertIsNone(capture.latest)


class ZedServerTests(InstallationServerTests):
    def setUp(self):
        super().setUp();self.capture=Mock();self.server.zed_capture=self.capture

    def test_native_start_stop_and_atomic_frame(self):
        self.assertEqual(self.request('/api/zed/start',{'X-Face-Avatar':'zed'},'POST')[0],202)
        self.capture.start.assert_called_once()
        self.capture.snapshot.return_value=({'version':1,'sequence':7,'ageMs':20},b'image')
        status,headers,body=self.request('/api/zed/frame')
        self.assertEqual(status,200);self.assertEqual(body,b'image')
        self.assertEqual(json.loads(headers['X-Zed-Sample'])['sequence'],7)
        self.assertEqual(self.request('/api/zed/stop',{'X-Face-Avatar':'zed'},'POST')[0],204)
        self.capture.stop.assert_called_once()

    def test_cross_site_and_rebinding_cannot_open_or_read_camera(self):
        for headers in [{'Host':'attacker.test'}, {'Sec-Fetch-Site':'cross-site'},{'Origin':'https://attacker.test'}]:
            self.assertEqual(self.request('/api/zed/frame',headers)[0],403)
            self.assertEqual(self.request('/api/zed/start',{**headers,'X-Face-Avatar':'zed'},'POST')[0],403)
        self.assertEqual(self.request('/api/zed/start',method='POST')[0],403)
        self.capture.start.assert_not_called();self.capture.snapshot.assert_not_called()

    def test_warmup_and_failure_do_not_serve_old_pixels(self):
        self.capture.snapshot.return_value=None
        self.assertEqual(self.request('/api/zed/frame')[0],204)
        self.capture.snapshot.side_effect=RuntimeError('camera disconnected')
        self.assertEqual(self.request('/api/zed/frame')[0],503)


if __name__=='__main__':unittest.main()
