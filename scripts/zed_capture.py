"""Single-owner, latest-frame ZED capture for the loopback installation server."""
import importlib
import math
import threading
import time
import uuid


def prerequisites():
    try:
        sl=importlib.import_module('pyzed.sl')
        cv2=importlib.import_module('cv2')
    except ImportError as error:
        raise RuntimeError('ZED mode needs the NVIDIA ZED SDK, its matching pyzed package, and OpenCV on the Orin. '+str(error)) from error
    return sl,cv2


class PersonSelector:
    def __init__(self):self.identity=None;self.last_seen=0

    def choose(self,people,now):
        for person in people:
            if person.id==self.identity:self.last_seen=now;return person
        if self.identity is not None and now-self.last_seen<.75:return None
        if not people:self.identity=None;return None
        person=min(people,key=lambda p:abs(float(p.position[0]))+.15*abs(float(p.position[2])))
        self.identity=person.id;self.last_seen=now;return person


def body_packet(body,sl,width,height):
    if body is None:return None
    joints={}
    for side in ['LEFT','RIGHT']:
        for part in ['SHOULDER','ELBOW','WRIST','HAND']:
            name=side+'_'+part;index=getattr(sl.BODY_34_PARTS,name).value
            p=[float(v) for v in body.keypoint[index]]
            image=[float(v) for v in body.keypoint_2d[index]]
            confidence=float(body.keypoint_confidence[index])
            if not all(math.isfinite(v) for v in p+image+[confidence]):continue
            joints[name]={'position':p,'image':[image[0]/width,image[1]/height],
                          'confidence':max(0,min(1,confidence/100))}
    return {'id':int(body.id),'joints':joints}


def visitor_region(bounds,joints,width,height):
    """Keep the selected person's outstretched hands inside the privacy mask."""
    points=[(float(p[0])*width,float(p[1])*height) for p in bounds
            if len(p)>=2 and all(math.isfinite(float(v)) for v in p[:2])]
    for joint in joints.values():
        image=joint.get('image',[])
        if joint.get('confidence',0)>=.6 and len(image)==2 and all(math.isfinite(v) and 0<=v<=1 for v in image):
            points.append((image[0]*width,image[1]*height))
    if not points:return None
    xs,ys=zip(*points);pad=max(12,(max(xs)-min(xs))*.1)
    x0,x1=min(xs)-pad,max(xs)+pad;y0,y1=min(ys)-pad,max(ys)+pad
    for side in ['LEFT','RIGHT']:
        wrist=joints.get(side+'_WRIST',{});elbow=joints.get(side+'_ELBOW',{})
        if wrist.get('confidence',0)<.6:continue
        p=wrist.get('image',[])
        if len(p)!=2 or not all(math.isfinite(v) and 0<=v<=1 for v in p):continue
        reach=max(12,width*.025)
        q=elbow.get('image',[])
        if elbow.get('confidence',0)>=.6 and len(q)==2 and all(math.isfinite(v) and 0<=v<=1 for v in q):
            reach=max(reach,math.hypot((p[0]-q[0])*width,(p[1]-q[1])*height)*.8)
        x,y=p[0]*width,p[1]*height
        x0=min(x0,x-reach);x1=max(x1,x+reach);y0=min(y0,y-reach);y1=max(y1,y+reach)
    return (max(0,min(width,int(x0))),max(0,min(height,int(y0))),
            max(0,min(width,math.ceil(x1))),max(0,min(height,math.ceil(y1))))


class ZedCapture:
    def __init__(self,serial=None):
        self.serial=serial;self.lock=threading.Lock();self.thread=None
        self.stop_event=threading.Event();self.latest=None;self.error=None
        self.last_request=0;self.session=None

    def start(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                if self.stop_event.is_set():raise RuntimeError('ZED is closing; retry shortly.')
                self.last_request=time.monotonic();return
            self.stop_event=threading.Event();self.latest=None;self.error=None
            self.session=uuid.uuid4().hex;self.last_request=time.monotonic()
            self.thread=threading.Thread(target=self.run,name='zed-capture',daemon=True)
            self.thread.start()

    def stop(self):
        self.stop_event.set()
        with self.lock:self.latest=None

    def snapshot(self):
        with self.lock:
            self.last_request=time.monotonic()
            if self.error:raise RuntimeError(self.error)
            if not self.latest:return None
            packet,jpeg,captured=self.latest
            age=(time.monotonic()-captured)*1000
            if age>250:return None
            return {**packet,'ageMs':age},jpeg

    def run(self):
        camera=None
        try:
            sl,cv2=prerequisites();camera=sl.Camera()
            init=sl.InitParameters()
            init.camera_resolution=sl.RESOLUTION.AUTO;init.camera_fps=30
            init.coordinate_units=sl.UNIT.METER
            init.coordinate_system=sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
            init.depth_mode=sl.DEPTH_MODE.NEURAL
            if self.serial:init.set_from_serial_number(self.serial)
            def check(code,operation):
                if code!=sl.ERROR_CODE.SUCCESS:raise RuntimeError(f'{operation}: {code}')
            check(camera.open(init),'Open ZED')
            if self.stop_event.is_set():return
            positional=sl.PositionalTrackingParameters();positional.set_as_static=True
            check(camera.enable_positional_tracking(positional),'ZED positional tracking')
            body=sl.BodyTrackingParameters()
            body.enable_tracking=True;body.enable_body_fitting=True
            body.body_format=sl.BODY_FORMAT.BODY_34
            body.detection_model=sl.BODY_TRACKING_MODEL.HUMAN_BODY_FAST
            body.prediction_timeout_s=0
            check(camera.enable_body_tracking(body),'ZED body tracking (requires a supported stereo/IMU model)')
            runtime=sl.RuntimeParameters();runtime.measure3D_reference_frame=sl.REFERENCE_FRAME.CAMERA
            body_runtime=sl.BodyTrackingRuntimeParameters();body_runtime.detection_confidence_threshold=60
            if hasattr(body_runtime,'skeleton_smoothing'):body_runtime.skeleton_smoothing=0
            info=camera.get_camera_information();resolution=info.camera_configuration.resolution
            width,height=resolution.width,resolution.height
            output=sl.Resolution(960,round(960*height/width))
            image=sl.Mat();bodies=sl.Bodies();selector=PersonSelector();sequence=0
            while not self.stop_event.is_set() and time.monotonic()-self.last_request<10:
                captured=time.monotonic()
                check(camera.grab(runtime),'ZED capture')
                check(camera.retrieve_bodies(bodies,body_runtime),'ZED skeleton')
                check(camera.retrieve_image(image,sl.VIEW.LEFT,sl.MEM.CPU,output),'ZED RGB')
                people=[p for p in bodies.body_list if p.tracking_state==sl.OBJECT_TRACKING_STATE.OK
                        and all(math.isfinite(float(v)) for v in p.position)]
                selected=selector.choose(people,captured)
                packet={'version':1,'session':self.session,'sequence':sequence,
                        'coordinates':'RIGHT_HANDED_Y_UP','reference':'CAMERA','units':'meters',
                        'body':body_packet(selected,sl,width,height)}
                pixels=cv2.cvtColor(image.get_data(),cv2.COLOR_BGRA2BGR)
                # Keep face and fingers on the selected visitor too. Black out
                # other people without cropping/rescaling the shared coordinates.
                masked=pixels.copy();masked[:]=0
                if selected is not None:
                    bounds=[(float(p[0])/width,float(p[1])/height) for p in selected.bounding_box_2d]
                    region=visitor_region(bounds,packet['body']['joints'],output.width,output.height)
                    if region:
                        x0,y0,x1,y1=region
                        masked[y0:y1,x0:x1]=pixels[y0:y1,x0:x1]
                ok,jpeg=cv2.imencode('.jpg',masked,[cv2.IMWRITE_JPEG_QUALITY,90])
                if not ok:raise RuntimeError('Cannot encode ZED RGB frame')
                with self.lock:
                    if not self.stop_event.is_set():self.latest=(packet,jpeg.tobytes(),captured)
                sequence+=1
        except Exception as error:
            with self.lock:self.error=str(error);self.latest=None
        finally:
            if camera is not None:camera.close()
            with self.lock:self.latest=None
