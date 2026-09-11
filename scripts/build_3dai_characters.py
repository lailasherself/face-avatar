"""Source-preserving character rigs fitted to reviewed Blender-space landmarks."""
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Quaternion
from mathutils.geometry import barycentric_transform

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build_avatar_fleet import CHANNELS, Mesh, material, export, clamp
from build_3dai_coral import smoothstep

OUT = ROOT/'assets/3dai/rigged'
QA = ROOT/'.context/qa/3dai'


class Character:
    def __init__(self, name, config, source):
        self.name, self.c, self.source = name, config, source
        self.body = bpy.data.objects[name.title()+'SourceBody']
        self.mx, self.mz, self.mw, self.curve = config['mouth']
        self.my = self.surface(self.mx, self.mz)[0].y
        self.eyes = []
        for x, z, rx, ry, rz in config['eyes']:
            front = self.surface(x, z)[0].y
            self.eyes.append((Vector((x, front+ry-.008, z)), Vector((rx, ry, rz))))
        self.mouth_rim = [self.surface(self.mx+self.mw*t/32, self.mouth_z(self.mx+self.mw*t/32))[0].y for t in range(-32,33)]

    def mouth_z(self, x):
        t = (x-self.mx)/self.mw
        return self.mz+self.curve*t*t+self.c.get('mouthWave',0)*math.cos(2*math.pi*t)

    def surface(self, x, z):
        hit, point, normal, index = self.body.ray_cast(Vector((x,-5,z)), Vector((0,1,0)))
        if not hit:
            return Vector((x, getattr(self,'my',-.4), z)), Vector((.5,.5))
        polygon = self.body.data.polygons[index]
        loops = list(polygon.loop_indices)[:3]
        points = [self.body.data.vertices[self.body.data.loops[i].vertex_index].co for i in loops]
        uv = self.body.data.uv_layers.active.data
        coords = [Vector((*uv[i].uv,0)) for i in loops]
        projected = barycentric_transform(point, *points, *coords)
        return point, Vector((projected.x, projected.y))

    def create_rig(self):
        data = bpy.data.armatures.new(self.name.title()+' body skeleton')
        rig = bpy.data.objects.new('AvatarRig', data)
        bpy.context.collection.objects.link(rig)
        bpy.context.view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        def bone(name, start, end, parent=None):
            b = data.edit_bones.new(name)
            b.head, b.tail = start, end
            if parent: b.parent = data.edit_bones[parent]
        hips, chest, neck, head = [Vector(self.c[k]) for k in ['hips','chest','neck','head']]
        spine = hips.lerp(chest,.45)
        bone('Root',(0,0,0),(0,0,.2))
        bone('Hips',hips,spine,'Root')
        bone('Spine',spine,chest,'Hips')
        bone('Chest',chest,neck,'Spine')
        bone('Neck',neck,neck.lerp(head,.12),'Chest')
        bone('Head',neck.lerp(head,.12),head,'Neck')
        for side,s in [('L',1),('R',-1)]:
            for names, points, parent in [(('UpperArm','Forearm','Hand'),self.c['arm'],'Chest'),(('Thigh','Shin','Foot'),self.c['leg'],'Hips')]:
                pts = [Vector((s*x,y,z)) for x,y,z in points]
                for i, name in enumerate(names):
                    bone(name+'.'+side,pts[i],pts[i+1],parent if i==0 else names[i-1]+'.'+side)
        for i,(a,b) in enumerate(zip(self.c.get('tail',[]),self.c.get('tail',[])[1:])):
            bone('Tail'+str(i+1),a,b,'Hips' if i==0 else 'Tail'+str(i))
        bpy.ops.object.mode_set(mode='OBJECT')
        rig.show_in_front = True
        rig['characterId'] = self.name
        rig['sourceTaskId'] = self.source['task_id']
        rig['cyclops'] = self.c.get('cyclops',False)
        rig['bodyRig'] = 'Fitted FK limbs, normalized four-influence skin; hands move as a unit'
        rig['facialRig'] = '52 deforming channels, geometric lids/gaze, cut mouth and oral cavity'
        rig.select_set(False)
        self.rig = rig

    def bind(self):
        body, rig = self.body, self.rig
        bpy.ops.object.select_all(action='DESELECT')
        body.select_set(True)
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')
        missing = [v for v in body.data.vertices if sum(g.weight for g in v.groups)<1e-8]
        assert len(missing)<len(body.data.vertices)*.05, (self.name,'bone heat failed',len(missing))
        # Flood only above the neck cut. Raised hands form separate components;
        # coordinate boxes alone accidentally pin fingers or free antenna tips.
        floor=self.c.get('headPinFloor',self.c['faceFloor'])
        eligible={v.index for v in body.data.vertices if v.co.z>floor}
        neighbors={i:[] for i in eligible}
        for edge in body.data.edges:
            a,b=edge.vertices
            if a in eligible and b in eligible:
                neighbors[a].append(b); neighbors[b].append(a)
        components=[]
        while eligible:
            todo=[eligible.pop()]; component=set(todo)
            while todo:
                for i in neighbors[todo.pop()]:
                    if i in eligible: eligible.remove(i); component.add(i); todo.append(i)
            components.append(component)
        head_vertices=max(components,key=len)
        for component in components:
            if min(body.data.vertices[i].co.z for i in component)>self.c['browZ']+.18:
                head_vertices.update(component)
        locked=[]
        for v in body.data.vertices:
            weights = sorted([(g.group,g.weight) for g in v.groups],key=lambda p:p[1],reverse=True)[:4]
            pin_head=v.index in head_vertices
            if abs(v.co.x)>self.c['headWidth'] and v.co.z<self.c['faceFloor']+.15:
                pin_head=False
            if self.name=='orbit':
                pin_head=v.co.z>2.25 or (v.co.z>1.52 and -.52<v.co.x<.66)
            if pin_head:
                head=smoothstep(floor,floor+.025,v.co.z)
                combined={i:w*(1-head) for i,w in weights}
                group=body.vertex_groups['Head'].index
                combined[group]=combined.get(group,0)+head
                weights=sorted(combined.items(),key=lambda p:p[1],reverse=True)[:4]
                if head>.999: locked.append(v.index)
            if self.c.get('tail') and v.co.y>.35 and v.co.z<self.c['hips'][2]+.3:
                tails=[b for b in rig.data.bones if b.name.startswith('Tail')]
                nearby=sorted(tails,key=lambda b:(v.co-b.head_local.lerp(b.tail_local,.5)).length)[:2]
                weights=[(body.vertex_groups[b.name].index,1/max(.015,(v.co-b.head_local.lerp(b.tail_local,.5)).length)**3) for b in nearby]
            if not weights:
                nearest = min(rig.data.bones,key=lambda b:(v.co-b.head_local.lerp(b.tail_local,.5)).length)
                weights = [(body.vertex_groups[nearest.name].index,1)]
            total = sum(w for _,w in weights)
            for group in [g.group for g in v.groups]: body.vertex_groups[group].remove([v.index])
            for group,w in weights: body.vertex_groups[group].add([v.index],w/total,'REPLACE')
        # Restrict heat's long-range influences to neighboring skeleton joints,
        # then relax weights across welded topology before the four-joint export.
        groups=list(body.vertex_groups)
        adjacency={g.index:set() for g in groups}
        for bone in rig.data.bones:
            if bone.parent:
                a=body.vertex_groups[bone.name].index; b=body.vertex_groups[bone.parent.name].index
                adjacency[a].add(b); adjacency[b].add(a)
        weights=np.zeros((len(body.data.vertices),len(groups)),dtype=np.float32)
        for v in body.data.vertices:
            for g in v.groups: weights[v.index,g.group]=g.weight
        allowed=np.zeros_like(weights)
        for i,primary in enumerate(weights.argmax(axis=1)):
            neighborhood={int(primary)}|adjacency[int(primary)]
            neighborhood.update(j for k in list(neighborhood) for j in adjacency[k])
            allowed[i,list(neighborhood)]=1
        weights*=allowed; weights/=np.maximum(1e-8,weights.sum(axis=1,keepdims=True))
        edges=np.array([edge.vertices[:] for edge in body.data.edges])
        degree=np.bincount(edges.ravel(),minlength=len(weights)).reshape(-1,1)
        for _ in range(45):
            total=np.zeros_like(weights)
            np.add.at(total,edges[:,0],weights[edges[:,1]])
            np.add.at(total,edges[:,1],weights[edges[:,0]])
            weights=weights*.35+total/np.maximum(1,degree)*.65
            weights/=np.maximum(1e-8,weights.sum(axis=1,keepdims=True))
            weights[locked]=0; weights[locked,body.vertex_groups['Head'].index]=1
        for v in body.data.vertices:
            strongest=np.argsort(weights[v.index])[-4:]
            total=sum(weights[v.index,g] for g in strongest)
            for group in [g.group for g in v.groups]: groups[group].remove([v.index])
            for group in strongest:
                w=float(weights[v.index,group]/total)
                if w>1e-8: groups[int(group)].add([v.index],w,'REPLACE')
        print('HEAT_BIND',self.name,'missing',len(missing),flush=True)

    def skin_delta(self, p, name, part='skin'):
        x,y,z = p
        X = x-self.mx
        mw = max(.12,self.mw)
        scale = max(.40,min(1.3,mw/.34))
        front = 1-smoothstep(self.my+.07,self.my+.36,y)
        floor, top = self.c['faceFloor'], self.c['faceTop']
        base_face = smoothstep(floor,floor+min(.09,(self.mz-floor)*.45),z)*(1-smoothstep(top-.04,top,z))*front
        face=base_face
        mask = 0
        for center,radii in self.eyes:
            if y<center.y+radii.y:
                r = ((x-center.x)/(radii.x*1.12))**2+((z-center.z)/(radii.z*1.12))**2
                mask = max(mask,1-smoothstep(1,1.7,r))
        if part=='skin': face *= 1-mask
        side = smoothstep(-mw*.2,mw*.2,X) if name.endswith('Left') else 1-smoothstep(-mw*.2,mw*.2,X) if name.endswith('Right') else 1
        mouth = math.exp(-((X/(mw*1.3))**6+((z-self.mz)/(.20*scale))**4))*face
        lower = 1-smoothstep(self.mz-.02*scale,self.mz+.012*scale,z)
        upper = 1-lower
        corner = clamp(abs(X)/mw)
        transition = .002+.11*scale*smoothstep(self.mw*.75,self.mw*1.2,abs(X))+.08*smoothstep(self.my+.02,self.my+.3,y)
        jaw = (1-smoothstep(self.mouth_z(x)-transition,self.mouth_z(x)+transition,z))*face
        if part in ['cavity','tongue']:
            mouth = 1
            jaw = 1-smoothstep(self.mouth_z(x)-.004,self.mouth_z(x)+.004,z)
        d = Vector((0,0,0))
        if name=='jawOpen':
            hinge = Vector((self.mx,self.my+.30*scale,self.mz+.10*scale))
            d = (Quaternion((1,0,0),.40)@(Vector(p)-hinge)+hinge-Vector(p))*jaw
        elif name=='mouthClose': return -self.skin_delta(p,'jawOpen',part)
        elif name in ['jawLeft','jawRight','jawForward']:
            if name=='jawForward': d.y = -.065*scale*jaw
            else: d.x = (.08 if name=='jawLeft' else -.08)*scale*jaw
        elif name in ['mouthLeft','mouthRight']: d.x = (.08 if name=='mouthLeft' else -.08)*scale*mouth
        elif name=='mouthFunnel':
            d.x = -X*.24*mouth; d.y = -.07*scale*mouth; d.z = (z-self.mz)*.5*mouth
        elif name=='mouthPucker': d.x = -X*.44*mouth; d.y = -.10*scale*mouth
        elif name.startswith('mouthSmile'):
            d.x = math.copysign(.055*scale,X)*corner*side*mouth; d.z = .11*scale*corner**1.3*side*mouth
        elif name.startswith('mouthFrown'): d.z = -.075*scale*corner*side*mouth
        elif name.startswith('mouthStretch'): d.x = math.copysign(.075*scale,X)*corner*side*mouth
        elif name.startswith('mouthDimple'): d.y = .05*scale*corner*side*mouth
        elif name.startswith('mouthPress'): d.z = -(z-self.mz)*.4*mouth*side
        elif name.startswith('mouthRoll'):
            w = lower if name.endswith('Lower') else upper
            d.y = .045*scale*w*mouth; d.z = (.018 if name.endswith('Lower') else -.018)*scale*w*mouth
        elif name.startswith('mouthShrug'):
            w = lower if name.endswith('Lower') else upper
            d.z = .055*scale*w*mouth; d.y = -.02*scale*w*mouth
        elif name.startswith('mouthLowerDown'): d.z = -.075*scale*lower*mouth*side
        elif name.startswith('mouthUpperUp'): d.z = .07*scale*upper*mouth*side
        elif name.startswith('brow'):
            width = max(abs(c.x-self.mx)+r.x for c,r in self.eyes)
            brow_scale=max(.65,min(1.3,self.c['headWidth']/.55))
            c,r=min(self.eyes,key=lambda eye:abs(x-eye[0].x))
            protected=mask*(1-smoothstep(c.z+r.z*.6,c.z+r.z*1.3,z))
            w = math.exp(-((abs(X)-width*.6)/(width*.7))**4-((z-self.c['browZ'])/(.11*brow_scale))**4)*base_face*(1-protected)
            if name=='browInnerUp': d.z = .07*brow_scale*w*(1-smoothstep(width*.05,width*.8,abs(X)))
            elif 'OuterUp' in name: d.z = .08*brow_scale*w*side*smoothstep(width*.2,width*.9,abs(X))
            else: d.z = -.06*brow_scale*w*side
        elif name=='cheekPuff' or name.startswith('cheekSquint'):
            w = math.exp(-((abs(X)-mw*.95)/(mw*.6))**2-((z-(self.mz+.13*scale))/(.15*scale))**2)*face
            if name=='cheekPuff': d.y = -.07*scale*w; d.x = math.copysign(.025*scale,X)*w
            else: d.z = .055*scale*w*side
        elif name.startswith('noseSneer'):
            w = math.exp(-(X/(mw*.65))**2-((z-self.mz-.12*scale)/(.12*scale))**2)*face*side
            d.z = .05*scale*w; d.y = -.02*scale*w
        if name=='tongueOut' and part=='tongue': d.y = -.35*scale; d.z = -.025*scale
        return d

    def cut_mouth(self):
        bm = bmesh.new(); bm.from_mesh(self.body.data)
        remove = []
        half = max(.006,min(.017,self.mw*.045))
        for f in bm.faces:
            x,y,z = f.calc_center_median()
            signed=[v.co.z-self.mouth_z(v.co.x) for v in f.verts]
            slit=half*math.sqrt(max(0,1-((x-self.mx)/self.mw)**2))
            if abs(x-self.mx)<self.mw*.98 and y<self.my+.15 and min(signed)<slit and max(signed)>-slit:
                remove.append(f)
        bmesh.ops.delete(bm,geom=remove,context='FACES')
        for v in bm.verts:
            x,y,z = v.co
            if v.is_boundary and abs(x-self.mx)<self.mw*1.10 and y<self.my+.15 and abs(z-self.mouth_z(x))<max(.07,half*4):
                v.co.z = self.mouth_z(x)+math.copysign(half*.65*math.sqrt(max(0,1-((x-self.mx)/(self.mw*1.04))**2)),z-self.mouth_z(x))
        bm.to_mesh(self.body.data); bm.free(); self.body.data.update()
        assert remove, (self.name,'no oral opening cut')
        return len(remove)

    def recess_source_eyes(self):
        for v in self.body.data.vertices:
            for c,r in self.eyes:
                radial=((v.co.x-c.x)/r.x)**2+((v.co.z-c.z)/r.z)**2
                if radial<1.16 and v.co.y<c.y+r.y*.4:
                    weight=1-smoothstep(.86,1.16,radial)
                    v.co.y+=(c.y+r.y*.4-v.co.y)*weight
        self.body.data.update()

    def baked_eye_material(self, i, lid=False):
        # Bake source UV samples into one continuous eye-local atlas. Interpolating
        # the original atlas UVs across newly tessellated triangles crosses islands.
        source_image=next(n.image for n in self.body.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and n.image)
        width,height=source_image.size
        source=np.empty(width*height*4,dtype=np.float32)
        source_image.pixels.foreach_get(source)
        source=source.reshape(height,width,4)
        c,r=self.eyes[i]; size=192
        pixels=np.empty((size,size,4),dtype=np.float32)
        for row in range(size):
            for column in range(size):
                x=c.x+r.x*(column/(size-1)*2-1)
                z=c.z+r.z*(row/(size-1)*2-1)
                if lid:
                    sx,sz=self.c['lidSample']
                    x=sx+(column/(size-1)*2-1)*.075
                    z=sz+(row/(size-1)*2-1)*.075
                uv=self.surface(x,z)[1]
                px=float(uv.x%1)*(width-1); py=float(uv.y%1)*(height-1)
                ix,iy=int(px),int(py); tx,ty=px-ix,py-iy
                pixels[row,column]=(source[iy,ix]*(1-tx)+source[iy,min(width-1,ix+1)]*tx)*(1-ty)+(source[min(height-1,iy+1),ix]*(1-tx)+source[min(height-1,iy+1),min(width-1,ix+1)]*tx)*ty
        image=bpy.data.images.new(self.name+(' lid ' if lid else ' iris ')+str(i),width=size,height=size,alpha=True)
        image.pixels.foreach_set(pixels.ravel()); image.pack()
        mat=material(image.name,'#ffffff',.6 if lid else .27)
        if lid:
            mat.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=0
            mat.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.25
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image=image
        mat.node_tree.links.new(tex.outputs['Color'],mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
        return mat

    def facial_targets(self):
        mesh = Mesh()
        eye = material(self.name+' sclera',self.c['eyeColor'],.30)
        pupil = material(self.name+' pupil',self.c['pupilColor'],.24)
        lid = material(self.name+' eyelid',self.c['lidColor'],.60)
        lid.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=.025
        dark = material(self.name+' oral interior','#200e20',.9)
        dark.node_tree.nodes['Principled BSDF'].inputs['Coat Weight'].default_value=0
        dark.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.025
        tongue = material(self.name+' tongue','#bd7183',.6)
        for i,(center,radii) in enumerate(self.eyes):
            ex,ey,ez = center; rx,ry,rz = radii
            mesh.ellipsoid(center,radii,eye,tag={'part':'eye','eye':i},n=40,rings=24)
            def pupil_surface(u,v):
                a = 2*math.pi*v
                size = self.c.get('pupilPatchAngle',1.48) if self.c.get('texturedIris') else self.c['pupilSize']
                t = .001+size*u
                px = math.sin(t)*math.cos(a)
                pz = math.sin(t)*math.sin(a)*self.c.get('pupilVertical',1)
                pz = clamp((pz+1)/2)*2-1
                norm = max(1,math.hypot(px,pz)/.998)
                px /= norm; pz /= norm
                return (ex+rx*px,ey-(ry+.002)*math.sqrt(max(.001,1-px*px-pz*pz)),ez+rz*pz)
            mesh.grid(12,40,pupil_surface,self.baked_eye_material(i) if self.c.get('texturedIris') else pupil,tag={'part':'pupil','eye':i})
            lid_material=self.baked_eye_material(i,True) if self.c.get('texturedLids') else lid
            for upper in [True,False]:
                angle = self.c['lidAngles'][0 if upper else 1]
                def point(u,v):
                    t=.001+u*angle; a=2*math.pi*v
                    return (ex+(rx+.006)*math.sin(t)*math.cos(a),ey+(ry+.006)*math.sin(t)*math.sin(a),ez+(1 if upper else -1)*(rz+.006)*math.cos(t))
                def tag(u,v,p): return {'part':'lid','eye':i,'u':u,'v':v,'upper':upper}
                mesh.grid(13,48,point,lid_material,tag=tag)
        def cavity(u,v):
            a=2*math.pi*v; x=self.mx+self.mw*math.cos(a)*(1-.25*u)
            t=clamp(((x-self.mx)/self.mw+1)/2)*64
            i=min(63,int(t)); y=self.mouth_rim[i]*(1-(t-i))+self.mouth_rim[i+1]*(t-i)
            return (x,y+.009+.27*u,self.mouth_z(x)+.015*math.sin(a)*(1+3*u))
        mesh.grid(9,64,cavity,dark,tag='cavity')
        mesh.ellipsoid((self.mx,self.my+.28,self.mz),(self.mw*.85,.045,.10),dark,tag='cavity',n=24,rings=12)
        mesh.ellipsoid((self.mx,self.my+.16,self.mz-.025),(self.mw*.43,.09,.017),tongue,tag='tongue',n=24,rings=12)
        face = mesh.object(self.name.title()+'EyesAndMouth',self.rig)
        uv = face.data.uv_layers.new(name='Source facial detail')
        mapped = []
        for p,tag in zip(mesh.v,mesh.tags):
            x,y,z = p
            if isinstance(tag,dict):
                c,r = self.eyes[tag['eye']]
                if tag['part']=='lid':
                    t=.001+tag['u']*(1.66 if tag['upper'] else 1.49)
                    x=c.x+r.x*math.sin(t)*math.cos(2*math.pi*tag['v'])
                    z=c.z+(1 if tag['upper'] else -1)*r.z*math.cos(t)
                mapped.append(Vector(((x-c.x)/r.x*.5+.5,(z-c.z)/r.z*.5+.5)))
            else: mapped.append(Vector((0,0)))
        for loop in face.data.loops: uv.data[loop.index].uv=mapped[loop.vertex_index]
        attr = face.data.attributes.new(name='_LID_INDEX',type='FLOAT',domain='POINT')
        attr.data.foreach_set('value',[t['eye']+1 if isinstance(t,dict) and t['part']=='lid' else 0 for t in mesh.tags])
        face['eyelidSurfaces']=[{'center':[c.x,c.z,-c.y],'radii':[r.x+.006,r.z+.006,r.y+.006]} for c,r in self.eyes]
        face['sourceTaskId']=self.source['task_id']
        face.shape_key_add(name='Basis',from_mix=False).value=0
        for name in CHANNELS:
            key=face.shape_key_add(name=name,from_mix=False); key.value=0
            for j,(p,tag) in enumerate(zip(mesh.v,mesh.tags)):
                d=Vector((0,0,0))
                if isinstance(tag,dict):
                    c,r=self.eyes[tag['eye']]
                    side='Left' if c.x>0 else 'Right'
                    if self.c.get('cyclops') or name.endswith(side):
                        if tag['part']=='lid' and name.startswith(('eyeBlink','eyeSquint','eyeWide')):
                            upper=tag['upper']; a=self.c['lidAngles'][0 if upper else 1]
                            if name.startswith('eyeBlink'): a=1.66 if upper else 1.49
                            elif name.startswith('eyeSquint'): a=min(1.61,a+.32)
                            else: a=max(.04,a-.5)
                            t=.001+tag['u']*a; phi=2*math.pi*tag['v']
                            q=Vector((c.x+(r.x+.006)*math.sin(t)*math.cos(phi),c.y+(r.y+.006)*math.sin(t)*math.sin(phi),c.z+(1 if upper else -1)*(r.z+.006)*math.cos(t)))
                            d=q-Vector(p)
                        elif tag['part']=='pupil' and name.startswith('eyeLook'):
                            q=Vector(((p[0]-c.x)/r.x,(p[1]-c.y)/r.y,(p[2]-c.z)/r.z))
                            if 'Up' in name: rot=Quaternion((1,0,0),-.28)
                            elif 'Down' in name: rot=Quaternion((1,0,0),.28)
                            else: rot=Quaternion((0,0,1),(-1 if 'In' in name else 1)*(1 if side=='Left' or self.c.get('cyclops') else -1)*.28)
                            dv=rot@q-q; d=Vector((dv.x*r.x,dv.y*r.y,dv.z*r.z))
                else: d=self.skin_delta(p,name,tag)
                key.data[j].co=Vector(p)+d
        self.recess_source_eyes()
        removed=self.cut_mouth()
        self.bind()
        self.body.shape_key_add(name='Basis',from_mix=False).value=0
        for name in CHANNELS:
            if name.startswith('eye') or name=='tongueOut': continue
            key=self.body.shape_key_add(name=name,from_mix=False); key.value=0
            for v in self.body.data.vertices: key.data[v.index].co=v.co+self.skin_delta(v.co,name)
        self.face,self.tags=face,mesh.tags
        return removed

    def aim(self, name, direction):
        b=self.rig.pose.bones[name]
        current=(b.tail-b.head).normalized()
        desired=current.rotation_difference(Vector(direction).normalized())@b.matrix.to_quaternion()
        parent=b.parent
        base=parent.matrix.to_quaternion()@parent.bone.matrix_local.to_quaternion().inverted()@b.bone.matrix_local.to_quaternion() if parent else b.bone.matrix_local.to_quaternion()
        b.rotation_quaternion=base.inverted()@desired
        bpy.context.view_layer.update()

    def pose(self, name):
        for b in self.rig.pose.bones:
            b.rotation_mode='QUATERNION'; b.rotation_quaternion=(1,0,0,0); b.location=(0,0,0)
        if name=='Seated':
            root=self.rig.pose.bones['Root']
            shift=Vector((0,.23-self.c['hips'][1],.84-self.c['hips'][2]))
            root.location=root.bone.matrix_local.to_quaternion().inverted()@shift
        bpy.context.view_layer.update()
        for side,s in [('L',1),('R',-1)]:
            if name=='T-Pose':
                self.aim('UpperArm.'+side,(s,0,0)); self.aim('Forearm.'+side,(s,0,0)); self.aim('Hand.'+side,(s,0,0))
            elif name=='Standing':
                self.aim('UpperArm.'+side,(s*.16,0,-1)); self.aim('Forearm.'+side,(s*.05,0,-1)); self.aim('Hand.'+side,(0,0,-1))
            else:
                self.aim('Thigh.'+side,(0,-1,0)); self.aim('Shin.'+side,(0,.05,-1)); self.aim('Foot.'+side,(0,-1,-.1))
                upper=self.rig.pose.bones['UpperArm.'+side]
                lower=self.rig.pose.bones['Forearm.'+side]
                shoulder=upper.head.copy(); goal=Vector((s*.47,-.48,1.12))
                axis=(goal-shoulder).normalized()
                a,b=upper.length,lower.length
                distance=min(a+b-.001,max(abs(a-b)+.001,(goal-shoulder).length))
                along=(a*a-b*b+distance*distance)/(2*distance)
                pole=Vector((s*.9,.05,1.02))-shoulder
                bend=(pole-axis*pole.dot(axis)).normalized()
                elbow=shoulder+axis*along+bend*math.sqrt(max(0,a*a-along*along))
                self.aim('UpperArm.'+side,elbow-shoulder)
                self.aim('Forearm.'+side,shoulder+axis*distance-lower.head)
                self.aim('Hand.'+side,(0,-.8,-.6))
        if name=='Seated':
            for i in range(len(self.c.get('tail',[]))-1):
                count=len(self.c['tail'])-1
                angle=.1+i*(5.3/(count-1) if self.name=='pearl' else 1.2/(count-1))
                self.aim('Tail'+str(i+1),(.10*math.sin(angle),math.cos(angle),math.sin(angle)))

    def actions(self):
        for name in ['Seated','Standing','T-Pose']:
            self.rig.animation_data_create(); self.rig.animation_data.action=None
            self.pose(name)
            for b in self.rig.pose.bones:
                for frame in [1,2]:
                    b.keyframe_insert('rotation_quaternion',frame=frame,group=b.name)
                    b.keyframe_insert('location',frame=frame,group=b.name)
            action=self.rig.animation_data.action; action.name=name
            track=self.rig.animation_data.nla_tracks.new(); track.name=name
            track.strips.new(name,1,action); track.mute=True
        self.rig.animation_data.action=None
        self.pose('Seated')

    def expression(self, values):
        if self.c.get('cyclops'):
            values=dict(values)
            for name in list(values):
                if name.startswith('eye') and name.endswith('Right'):
                    values[name[:-5]+'Left']=max(values.get(name[:-5]+'Left',0),values[name]); values[name]=0
        for obj in [self.body,self.face]:
            for key in obj.data.shape_keys.key_blocks: key.value=values.get(key.name,0)

    def render(self):
        scene=bpy.context.scene; camera=scene.camera
        scene.render.resolution_x=800; scene.render.resolution_y=800; scene.cycles.samples=12
        bpy.ops.import_scene.gltf(filepath=str(OUT/'silver-vehicle.glb'))
        car=[o for o in scene.objects if o.get('assetRole')=='shared-vehicle']
        camera.location=(3.8,-7,3.3)
        camera.rotation_euler=(Vector((0,0,1.6))-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.ortho_scale=4.3
        self.pose('Seated'); self.expression({})
        bpy.ops.object.select_all(action='DESELECT')
        self.rig.select_set(True); bpy.context.view_layer.objects.active=self.rig
        scene['rigReview']='Source-based '+self.name+'. Original preserved. FK limbs and facial morphs; artistic/live-camera review pending.'
        bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'blender/3dai'/(self.name+'-rigged.blend')))
        scene.render.filepath=str(OUT/(self.name+'.png')); bpy.ops.render.render(write_still=True)
        for obj in car: obj.hide_render=True
        for pose in ['Standing','T-Pose']:
            self.pose(pose)
            camera.location=(0,-8,1.6); camera.rotation_euler=(math.pi/2,0,0); camera.data.ortho_scale=3.7
            scene.render.filepath=str(QA/(self.name+'-'+pose.lower()+'.png')); bpy.ops.render.render(write_still=True)
        self.pose('Standing')
        center=(self.mz+max(c.z+r.z for c,r in self.eyes))*.5
        camera.location=(.03,-8,center); camera.rotation_euler=(Vector((0,0,center))-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.ortho_scale=max(1.2,self.c['headWidth']*2.3)
        cases={'neutral':{},'jaw':{'jawOpen':1},'smile':{'mouthSmileLeft':1,'mouthSmileRight':1,'jawOpen':.2},
               'blink-left':{'eyeBlinkLeft':1},'blink-both':{'eyeBlinkLeft':1,'eyeBlinkRight':1},
               'brows':{'browInnerUp':1,'browOuterUpLeft':1,'browOuterUpRight':1},'gaze':{'eyeLookOutLeft':1,'eyeLookInRight':1}}
        if '--quick' in sys.argv: cases={k:cases[k] for k in ['neutral','jaw','blink-both']}
        for name,values in cases.items():
            self.expression(values)
            scene.render.filepath=str(QA/(self.name+'-'+name+'.png')); bpy.ops.render.render(write_still=True)


def main():
    configs=json.loads((ROOT/'scripts/rig_3dai_landmarks.json').read_text())
    sources={s['name']:s for s in json.loads((ROOT/'assets/3dai/selection.json').read_text())['characters']}
    requested=[n for n in sys.argv[sys.argv.index('--')+1:] if not n.startswith('--')] if '--' in sys.argv else []
    for name,c in configs.items():
        if requested and name not in requested: continue
        bpy.ops.wm.open_mainfile(filepath=str(ROOT/'blender/3dai'/(name+'-prepared.blend')))
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.object.select_all(action='DESELECT')
        character=Character(name,c,sources[name])
        character.create_rig()
        removed=character.facial_targets()
        character.actions()
        export(OUT/(name+'.glb'),[character.rig,character.body,character.face],True)
        character.render()
        report={'character':name,'bones':len(character.rig.data.bones),'mouthFacesRemoved':removed,
                'mouthFront':character.my,'eyes':[{'center':list(c),'radii':list(r)} for c,r in character.eyes]}
        (QA/(name+'-build.json')).write_text(json.dumps(report,indent=2)+'\n')
        print('BUILT',json.dumps(report),flush=True)


if __name__=='__main__': main()
