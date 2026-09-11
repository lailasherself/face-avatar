"""Reference-contour Kudzu build, executed in stages through live Blender MCP.

Uses the approved Clay workflow's mesh utilities, not the rejected generic face.
Original assets and the installation roster are never replaced here.
"""
import bpy
import bmesh
import math
import json
from pathlib import Path
from mathutils import Vector, Quaternion
from mathutils.geometry import delaunay_2d_cdt
from complete_clay_likeness import mesh, closed_rings, plain_material, smooth, profile
from build_avatar_fleet import CHANNELS

ROOT=Path(__file__).resolve().parents[1]
REF=ROOT/'.context/attachments/IJ8Kw9/lailasherself_cosmic_alien_creature_made_of_glowing_kudzu_vin_a6ef611d-6e1e-4386-b640-c9eff69d7e00_2.png'
OUT=ROOT/'blender/likeness-trials/kudzu-body-rig.blend'
GLB=ROOT/'assets/likeness-trials/kudzu-body-rig.glb'
QA=ROOT/'.context/qa/kudzu-complete'
SCALE=330
OUTLINE=[(239,261),(285,248),(341,251),(403,248),(455,260),(510,281),(544,313),(565,363),(572,421),(570,486),(557,548),(535,589),(482,609),(419,619),(351,620),(288,612),(229,597),(197,578),(179,546),(165,500),(153,447),(151,400),(162,349),(185,309),(216,280)]
MOUTH=(.06,(1194-524)/330)
ARMS={'R':[(-.235,0,1.57),(-.409,-.01,1.04),(-.50,-.035,.70),(-.525,-.055,.585)],
      'L':[(.240,0,1.57),(.425,-.01,1.04),(.565,-.035,.70),(.585,-.055,.585)]}
ARM_RADII={s:[.105,.080,.067,.068] for s in ARMS}
TORSO=[(.79,0,.19,.13),(.89,0,.25,.18),(1.08,0,.245,.17),(1.35,0,.25,.18),(1.55,0,.22,.155),(1.74,0,.145,.12),(1.88,0,.15,.13)]
LEGS={s:[(.014,x,.072,.09),(.055,x,.12,.17),(.13,x,.11,.15),(.26,x,.07,.08),(.49,x,.08,.09),(.72,x,.105,.11),(.89,x*.85,.10,.10),(.99,x*.65,.055,.06)] for s,x in [('R',-.13),('L',.21)]}
DIGITS={}
for side,p in ARMS.items():
    sign=1 if side=='L' else -1;x=p[-1][0]
    DIGITS[side]={'Thumb':[(x-sign*.045,-.05,.61),(x-sign*.080,-.07,.57),(x-sign*.11,-.09,.53),(x-sign*.12,-.10,.515)],
                  'Index':[(x+sign*.04,-.05,.57),(x+sign*.055,-.07,.51),(x+sign*.05,-.09,.46),(x+sign*.025,-.10,.435)],
                  'Middle':[(x-sign*.01,-.05,.555),(x-sign*.014,-.075,.50),(x-sign*.025,-.10,.455),(x-sign*.04,-.11,.44)]}


def obj(name):return bpy.context.scene.objects[name]
def point(x,z,y=0):return Vector(((x-360)/SCALE,y,(1194-z)/SCALE))


def loop(points,steps=5):
    out=[]
    for i in range(len(points)):
        a,b,c,d=[Vector(points[j%len(points)]) for j in (i-1,i,i+1,i+2)]
        for j in range(steps):
            t=j/steps;out.append(.5*(2*b+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return out


def inside(p,poly):
    odd=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a.y>p.y)!=(b.y>p.y) and p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x:odd=not odd
    return odd


def contour():return [Vector((p.x,p.z)) for p in [point(*v) for v in loop(OUTLINE)]]


def depth(p,outline=None):
    outline=outline or contour();cx,cz=0,2.321;dx,dz=p[0]-cx,p[1]-cz
    if abs(dx)+abs(dz)<1e-8:return -.375
    hits=[]
    for a,b in zip(outline,outline[1:]+outline[:1]):
        ex,ez=b.x-a.x,b.y-a.y;det=dx*ez-dz*ex
        if abs(det)<1e-10:continue
        ax,az=a.x-cx,a.y-cz;t=(ax*ez-az*ex)/det;u=(ax*dz-az*dx)/det
        if t>0 and -1e-6<=u<=1.000001:hits.append(t)
    r=1/min(hits) if hits else 1
    return -.375*math.sqrt(max(0,1-r*r))


def scene():
    QA.mkdir(parents=True,exist_ok=True);s=bpy.data.scenes.new('Kudzu - Reference Contour Character');bpy.context.window.scene=s
    s['status']='Reference-based body/face rig in progress; isolated from installation.'
    s['source_reference']=str(REF)
    mats={name:plain_material('Kudzu '+name,color,rough) for name,color,rough in [
        ('Galaxy',(.07,.006,.12),.65),('Orange',(.95,.19,.001),.60),('Green',(.002,.27,.003),.65),
        ('Eye',(.001,.005,.0015),.11),('Oral interior',(.002,.0003,.001),.95),
        ('Tongue',(.44,.055,.13),.44),('Teeth',(.84,.75,.57),.34)]}
    for name in ['Orange','Green']:mats[name].node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.18
    s['material_names']={name:m.name for name,m in mats.items()}
    reference=bpy.data.objects.new('Kudzu source - comparison only',None);s.collection.objects.link(reference)
    reference.empty_display_type='IMAGE';reference.data=bpy.data.images.load(str(REF),check_existing=True);reference.data.pack()
    reference.empty_display_size=1344/SCALE;reference.location=(-2.7,.8,(1194-672)/SCALE);reference.rotation_euler=(math.pi/2,0,0);reference.hide_render=True
    world=bpy.data.worlds.new('Kudzu review world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.18,.18,1);world.node_tree.nodes['Background'].inputs[1].default_value=.45;s.world=world
    for name,loc,power,size in [('Key',(-3,-4,6),420,4),('Fill',(3,-3,3),160,3),('Rim',(1,3,5),260,3)]:
        d=bpy.data.lights.new('Kudzu '+name,'AREA');o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.8))-o.location).to_track_quat('-Z','Y').to_euler();d.energy=power;d.size=size
    d=bpy.data.cameras.new('Kudzu Camera');o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);s.camera=o;d.type='ORTHO';d.ortho_scale=3.9
    s.render.engine='CYCLES';s.cycles.samples=32;s.render.resolution_x=1100;s.render.resolution_y=1400;s.render.resolution_percentage=100
    s.view_settings.view_transform='Standard';view()
    print('Separate Kudzu scene created; Clay remains preserved.')


def material(name):return bpy.data.materials[bpy.context.scene['material_names'][name]]


def head():
    outline=contour();front=[Vector((p.x*.94,2.321+(p.y-2.321)*.94)) for p in outline]
    n=120;mouth=[Vector((MOUTH[0]+.48*math.cos(j*math.tau/n),MOUTH[1]+.21*math.sin(j*math.tau/n))) for j in range(n)]
    coords=list(front)+mouth;count=len(outline)
    edges=[(i,(i+1)%count) for i in range(count)]+[(count+j,count+(j+1)%n) for j in range(n)]
    for r in [.92,.86,.78,.68,.57,.45,.32,.19,.08]:
        for p in outline:
            q=Vector((p.x*r,2.321+(p.y-2.321)*r))
            if not inside(q,mouth):coords.append(q)
    dv,de,df,ov,oe,of=delaunay_2d_cdt(coords,edges,[],0,1e-7)
    mapping={original:i for i,ids in enumerate(ov) for original in ids}
    verts=[Vector((p.x,depth(p,outline),p.y)) for p in dv];faces=[]
    for face in df:
        p=sum((dv[i] for i in face),Vector((0,0)))/len(face)
        if inside(p,front) and not inside(p,mouth):faces.append(tuple(face))
    previous=[mapping[i] for i in range(count)]
    for r in [.96,.98,.995,1]:
        current=[]
        for p in outline:
            q=Vector((p.x*r,2.321+(p.y-2.321)*r));current.append(len(verts));verts.append(Vector((q.x,depth(q,outline),q.y)))
        for j in range(count):faces.append((previous[j],previous[(j+1)%count],current[(j+1)%count],current[j]))
        previous=current
    for r in [.996,.985,.96,.92,.86,.78,.68,.57,.45,.32,.19,.08]:
        current=[]
        for p in outline:current.append(len(verts));verts.append(Vector((p.x*r,.30*math.sqrt(1-r*r),2.321+(p.y-2.321)*r)))
        for j in range(count):faces.append((previous[j],previous[(j+1)%count],current[(j+1)%count],current[j]))
        previous=current
    center=len(verts);verts.append(Vector((0,.30,2.321)))
    faces.extend((previous[j],previous[(j+1)%count],center) for j in range(count))
    previous=[mapping[count+j] for j in range(n)];patch=[];start=len(verts)
    levels=[.07,.15,.25,.36,.48,.60,.71,.81,.89,.94,.975,1]
    for t in levels:
        current=[]
        for j in range(n):
            phi=j*math.tau/n;sn=math.sin(phi)
            inner=Vector((MOUTH[0]+.405*math.cos(phi),MOUTH[1]+-.045*sn*sn+.018*math.cos(phi)+(.008 if sn>=0 else .006)*sn))
            q=mouth[j].lerp(inner,t);current.append(len(verts));patch.append((len(verts),j,t));verts.append(Vector((q.x,depth(q,outline),q.y)))
        for j in range(n):faces.append((previous[j],previous[(j+1)%n],current[(j+1)%n],current[j]))
        previous=current
    h=mesh('Kudzu Head',verts,faces,material('Galaxy'));h['mouthPatchStart']=start;h['mouthPatchRingSize']=n;h['armCollisionSurface']=True
    print({'head_vertices':len(verts),'mouth_quad_rings':12,'source_outline_points':len(outline)})


def tube(name,points,radii,mat,rings=60,sides=40):
    pts=[Vector(p) for p in points];data=[]
    for i in range(rings):
        t=i/(rings-1);u=t*(len(pts)-1);k=min(len(pts)-2,int(u));f=u-k
        a0,b0,c0,d0=pts[max(0,k-1)],pts[k],pts[k+1],pts[min(len(pts)-1,k+2)]
        p=.5*(2*b0+(-a0+c0)*f+(2*a0-5*b0+4*c0-d0)*f*f+(-a0+3*b0-3*c0+d0)*f*f*f)
        direction=(.5*((-a0+c0)+2*(2*a0-5*b0+4*c0-d0)*f+3*(-a0+3*b0-3*c0+d0)*f*f)).normalized()
        a=direction.cross(Vector((0,1,0))).normalized();b=direction.cross(a).normalized()
        r=profile([(j/(len(radii)-1),v) for j,v in enumerate(radii)],t)
        data.append([p+r*(a*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides)) for j in range(sides)])
    return closed_rings(name,data,mat)


def ellipsoid(name,center,radii,mat,nr=32,nc=56):
    rings=[]
    for i in range(nr+1):
        theta=math.pi*(.001+.998*i/nr)
        rings.append([(center[0]+radii[0]*math.sin(theta)*math.cos(j*math.tau/nc),center[1]+radii[1]*math.sin(theta)*math.sin(j*math.tau/nc),center[2]+radii[2]*math.cos(theta)) for j in range(nc)])
    return closed_rings(name,rings,mat)


def body():
    from reference_body_tools import body as build
    build('Kudzu',material('Galaxy'),TORSO,{s:(p,ARM_RADII[s]) for s,p in ARMS.items()},LEGS,DIGITS)

def fuse_body():pass

def eyes():
    for side,px,py in [('R',286,425),('L',491,422)]:
        center=point(px,py,-.34);radii=Vector((.221,.203,.207))
        eye=ellipsoid('Kudzu Eye '+side,center,radii,material('Eye'))
        pupil_mat=bpy.data.materials.get('Kudzu Pupil') or plain_material('Kudzu Pupil',(.0001,.002,.0001),.40)
        vs=[];fs=[];nc=64
        for row in range(1,17):
            r=row/16
            for j in range(nc):
                x=.098*r*math.cos(j*math.tau/nc);z=.018+.105*r*math.sin(j*math.tau/nc);y=-radii.y*math.sqrt(max(0,1-(x/radii.x)**2-(z/radii.z)**2))-.002;vs.append(center+Vector((x,y,z)))
        for row in range(15):
            for j in range(nc):fs.append((row*nc+j,row*nc+(j+1)%nc,(row+1)*nc+(j+1)%nc,(row+1)*nc+j))
        ci=len(vs);vs.append(center+Vector((0,-radii.y*math.sqrt(1-(.018/radii.z)**2)-.002,.018)));fs.extend((j,(j+1)%nc,ci) for j in range(nc));mesh('Kudzu Pupil '+side,vs,fs,pupil_mat)
        for part,mat in [('Upper','Orange'),('Lower','Green')]:
            nr,nc=25,80;vs=[];faces=[]
            for row in range(nr):
                u=row/(nr-1);theta=.002+(1.55-.002)*u if part=='Upper' else 2.58+(math.pi-.002-2.58)*u
                for j in range(nc):
                    phi=j*math.tau/nc;vs.append(center+Vector((radii.x*math.sin(theta)*math.cos(phi),radii.y*math.sin(theta)*math.sin(phi),radii.z*math.cos(theta)))*1.018)
            for row in range(nr-1):
                for j in range(nc):faces.append((row*nc+j,row*nc+(j+1)%nc,(row+1)*nc+(j+1)%nc,(row+1)*nc+j))
            lid=mesh('Kudzu '+part+' Lid '+side,vs,faces,material(mat));lid['lidCenter']=list(center);lid['lidRadii']=list(radii);lid['lidPart']=part;lid['lidSide']=side
    print('Orange upper and green lower volumetric eyelids fitted to glossy eyes.')


def galaxy():
    m=material('Galaxy');n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF'];p.inputs['Roughness'].default_value=.55;p.inputs['Specular IOR Level'].default_value=.18
    tc=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=6;l.new(tc.outputs['Object'],noise.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(.0003,.016,.0005,1);ramp.color_ramp.elements[1].color=(.002,.11,.006,1);l.new(noise.outputs['Fac'],ramp.inputs[0])
    vor=n.new('ShaderNodeTexVoronoi');vor.inputs['Scale'].default_value=100;l.new(tc.outputs['Object'],vor.inputs['Vector'])
    fleck=n.new('ShaderNodeValToRGB');fleck.color_ramp.elements[0].position=.045;fleck.color_ramp.elements[0].color=(.46,.92,.0005,1);fleck.color_ramp.elements[1].position=.23;fleck.color_ramp.elements[1].color=(0,0,0,1);l.new(vor.outputs['Distance'],fleck.inputs[0])
    mix=n.new('ShaderNodeMixRGB');mix.blend_type='ADD';mix.inputs[0].default_value=1;l.new(ramp.outputs[0],mix.inputs[1]);l.new(fleck.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],p.inputs['Base Color'])
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.10;bump.inputs['Distance'].default_value=.0015;l.new(vor.outputs['Distance'],bump.inputs['Height']);l.new(bump.outputs[0],p.inputs['Normal'])
    for name in ['Orange','Green']:material(name).node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.002,.055,.008,1)
    p=material('Eye').node_tree.nodes['Principled BSDF'];p.inputs['Base Color'].default_value=(.80,.42,.16,1);p.inputs['Roughness'].default_value=.45
    m['source']='New volumetric forest-green skin and lime flecks; source PNG used for comparison only.'


def skeleton():
    from reference_body_tools import rig
    return rig('Kudzu',TORSO,{s:(p,ARM_RADII[s]) for s,p in ARMS.items()},LEGS,DIGITS,.89,.49,.14,1.88,2.6,1.15,.34,iterations=1300)

def mouth_point(j,n=120):
    phi=j*math.tau/n;sn=math.sin(phi);x=MOUTH[0]+.405*math.cos(phi);z=MOUTH[1]-.045*sn*sn+.018*math.cos(phi)+(.008 if sn>=0 else .006)*sn
    return Vector((x,depth((x,z)),z))


def smooth_shoulders(iterations=750):pass

def runtime_weights():pass

def mouth_motion(j,name):
    phi=j*math.tau/120;q=math.cos(phi);sn=math.sin(phi);p=mouth_point(j);v=p.copy();side=1 if name.endswith('Left') else -1
    mask=smooth(-.25,.55,q*side);top=max(0,sn);bottom=max(0,-sn)
    if name in {'jawOpen','mouthClose'}:
        target=Vector((MOUTH[0]+.38*q,0,MOUTH[1]-.045+.112*sn));target.y=depth((target.x,target.z));return (target-p)*(1 if name=='jawOpen' else -1)
    if name in {'jawLeft','jawRight','mouthLeft','mouthRight'}:v.x+=side*.028
    elif name=='jawForward':v.y-=.018
    elif name.startswith('mouthSmile'):v.z+=.012*mask*abs(q);v.x+=side*.0048*mask
    elif name.startswith('mouthFrown'):v.z-=.018*mask*abs(q)
    elif name.startswith('mouthDimple'):v.x+=side*.012*mask;v.y+=.009*mask
    elif name.startswith('mouthStretch'):v.x+=side*.028*mask
    elif name in {'mouthPucker','mouthFunnel'}:v.x=MOUTH[0]+(v.x-MOUTH[0])*(.84 if name=='mouthPucker' else .90);v.z+=.030*sn;v.y-=.02
    elif name=='mouthRollUpper':v.z-=.003*top;v.y+=.008*top
    elif name=='mouthRollLower':v.z+=.003*bottom;v.y+=.008*bottom
    elif name=='mouthShrugUpper':v.z+=.025*top
    elif name=='mouthShrugLower':v.z+=.014*bottom
    elif name.startswith('mouthPress'):v.z-=.002*sn*mask
    elif name.startswith('mouthUpperUp'):v.z+=.033*top*mask
    elif name.startswith('mouthLowerDown'):v.z-=.030*bottom*mask
    return v-p


def facial():
    h=obj('Kudzu Head');base=h.shape_key_add(name='Basis',from_mix=False);start=h['mouthPatchStart'];n=120;levels=[.07,.15,.25,.36,.48,.60,.71,.81,.89,.94,.975,1]
    outline=contour()
    for name in CHANNELS:
        if name=='tongueOut':continue
        key=h.shape_key_add(name=name,from_mix=False)
        for v,b in zip(key.data,base.data):v.co=b.co
        if name.startswith(('jaw','mouth')):
            deltas=[mouth_motion(j,name) for j in range(n)]
            for row,t in enumerate(levels):
                for j in range(n):
                    index=start+row*n+j;v=base.data[index].co+deltas[j]*t
                    v.y=depth((v.x,v.z),outline)+(0 if name in {'jawOpen','mouthClose'} else deltas[j].y)*t
                    key.data[index].co=v
        else:
            for v,b in zip(key.data,base.data):
                x,y,z=b.co;front=smooth(.0,-.25,y);side=1 if name.endswith('Left') else -1;local=math.exp(-((x-side*.30)/.24)**4)
                if name.startswith('brow'):v.co.z+=(.025 if 'Up' in name else -.020)*front*local*math.exp(-((z-2.66)/.15)**4)
                elif name=='cheekPuff':v.co.y-=.025*front*math.exp(-((z-2.02)/.18)**4)*smooth(.25,.50,abs(x))
                elif name.startswith('cheekSquint'):v.co.z+=.012*front*local*math.exp(-((z-2.04)/.13)**4)
                elif name.startswith('noseSneer'):v.co.z+=.015*front*local*math.exp(-((z-2.18)/.13)**4)
    for side,label in [('L','Left'),('R','Right')]:
        for part in ['Upper','Lower']:
            lid=obj(f'Kudzu {part} Lid {side}');base=lid.shape_key_add(name='Basis',from_mix=False);center=Vector(lid['lidCenter']);r=Vector(lid['lidRadii']);nr,nc=25,80
            for channel,boundary in [('eyeBlink',1.73 if part=='Upper' else 1.733),('eyeWide',1.22 if part=='Upper' else 2.72),('eyeSquint',1.67 if part=='Upper' else 2.40)]:
                key=lid.shape_key_add(name=channel+label,from_mix=False)
                for row in range(nr):
                    u=row/(nr-1);theta=.002+(boundary-.002)*u if part=='Upper' else boundary+(math.pi-.002-boundary)*u
                    for j in range(nc):
                        phi=j*math.tau/nc;key.data[row*nc+j].co=center+Vector((r.x*math.sin(theta)*math.cos(phi),r.y*math.sin(theta)*math.sin(phi),r.z*math.cos(theta)))*1.018
            lid['blinkMethod']='Parameterized matched shell boundaries; production resolveEyeAperture prevents opposing morphs.'
        eye=obj('Kudzu Eye '+side);base=eye.shape_key_add(name='Basis',from_mix=False)
        for axis,direction in [('In',-.010 if side=='L' else .010),('Out',.010 if side=='L' else -.010),('Up',.008),('Down',-.008)]:
            key=eye.shape_key_add(name='eyeLook'+axis+label,from_mix=False)
            for v,b in zip(key.data,base.data):v.co=b.co+Vector((direction,0,0) if axis in ['In','Out'] else (0,0,direction))
    for side,label in [('L','Left'),('R','Right')]:
        pupil=obj('Kudzu Pupil '+side);base=pupil.shape_key_add(name='Basis',from_mix=False)
        for axis,d in [('In',-.022 if side=='L' else .022),('Out',.022 if side=='L' else -.022),('Up',.016),('Down',-.016)]:
            k=pupil.shape_key_add(name='eyeLook'+axis+label,from_mix=False)
            for v,b in zip(k.data,base.data):v.co=b.co+Vector((d,0,0) if axis in ['In','Out'] else (0,0,d))
    oral()
    print('52 expression channels, independently fitted eyelids and bounded mouth loops created.')


def bind_head(o):
    rig=obj('Kudzu AvatarRig');g=o.vertex_groups.new(name='Head');g.add(list(range(len(o.data.vertices))),1,'REPLACE');o.parent=rig;m=o.modifiers.new('Head deformation','ARMATURE');m.object=rig


def oral():
    n=120;inner=[mouth_point(j) for j in range(n)]
    rings=[[(p.x*(1+.15*t),p.y+.004+.28*t,p.z-.02*t+(p.z-MOUTH[1])*t*2) for p in inner] for t in [i/12 for i in range(13)]]
    cavity=closed_rings('Kudzu Oral Cavity',rings,material('Oral interior'))
    bm=bmesh.new();bm.from_mesh(cavity.data);bm.verts.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.verts[13*n]],context='VERTS');bm.to_mesh(cavity.data);bm.free();bind_head(cavity)
    base=cavity.shape_key_add(name='Basis',from_mix=False)
    for name in CHANNELS:
        if not name.startswith(('mouth','jaw')):continue
        key=cavity.shape_key_add(name=name,from_mix=False)
        deltas=[mouth_motion(j,name) for j in range(n)]
        for i,(v,b) in enumerate(zip(key.data,base.data)):v.co=b.co+deltas[i%n]*(1-smooth(.1,.8,min(1,i//n/12)))
    for row,zc in [('Upper',MOUTH[1]+.063),('Lower',MOUTH[1]-.045)]:
        parts=[]
        for i in range(8):parts.append(ellipsoid(f'Kudzu {row} Tooth {i}',(MOUTH[0]+(i-3.5)*.057,-.215+abs(i-3.5)*.004,zc),(.025,.035,.035),material('Teeth'),nr=8,nc=16))
        bpy.ops.object.select_all(action='DESELECT')
        for o in parts:o.select_set(True)
        bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=bpy.context.object;o.name='Kudzu '+row+' Teeth';bind_head(o);base=o.shape_key_add(name='Basis',from_mix=False)
        for name,sign in [('jawOpen',1),('mouthClose',-1)]:
            key=o.shape_key_add(name=name,from_mix=False)
            for v,b in zip(key.data,base.data):v.co=b.co+Vector((0,0,sign*(-.005 if row=='Upper' else -.08)))
    rings=[];nr,nc=49,24
    for i in range(nr):
        t=i/(nr-1);tip=math.sqrt(max(.02,1-t**8));rings.append([(MOUTH[0]+.095*tip*math.cos(j*math.tau/nc),-.10-.10*t,MOUTH[1]-.037+.021*tip*math.sin(j*math.tau/nc)) for j in range(nc)])
    tongue=closed_rings('Kudzu Long Tongue',rings,material('Tongue'));bind_head(tongue);base=tongue.shape_key_add(name='Basis',from_mix=False)
    for name in ['tongueOut','jawOpen','mouthClose']:
        key=tongue.shape_key_add(name=name,from_mix=False)
        for i,(v,b) in enumerate(zip(key.data,base.data)):
            t=(i//nc)/(nr-1) if i<nr*nc else (0 if i==nr*nc else 1);v.co=b.co
            if name=='tongueOut':v.co.y-=.98*t;v.co.z+=.11*math.sin(math.pi*t)-.42*t*t
            else:v.co.z-=(-1 if name=='mouthClose' else 1)*.04*smooth(0,.38,t)
    tongue['tongueRootAnchored']=True;tongue['additionalReach']=.98


def reset():
    for o in bpy.context.scene.objects:
        if o.type=='ARMATURE':
            for p in o.pose.bones:p.rotation_mode='QUATERNION';p.rotation_quaternion=Quaternion();p.location=(0,0,0);p.scale=(1,1,1)
        if o.type=='MESH' and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:k.value=0
    bpy.context.view_layer.update()


def expression(values):
    for o in bpy.context.scene.objects:
        if o.type=='MESH' and o.data.shape_keys:
            for k in o.data.shape_keys.key_blocks:k.value=values.get(k.name,0)
    bpy.context.view_layer.update()


def rotate(name,axis,angle):
    p=obj('Kudzu AvatarRig').pose.bones[name];p.rotation_mode='QUATERNION';p.rotation_quaternion=Quaternion(Vector(axis),angle);bpy.context.view_layer.update()


def bake_material():
    reset();s=bpy.context.scene;s.cycles.samples=8;skin=material('Galaxy');skin.use_fake_user=True
    objects=[o for o in s.objects if o.type=='MESH' and skin in list(o.data.materials)]
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.010);bpy.ops.object.mode_set(mode='OBJECT')
    images=[];node=skin.node_tree.nodes.new('ShaderNodeTexImage');skin.node_tree.nodes.active=node
    for name,size,kind in [('basecolor',2048,'DIFFUSE'),('normal',1024,'NORMAL')]:
        atlas=bpy.data.images.new('Kudzu galaxy '+name,width=size,height=size);node.image=atlas
        if kind=='NORMAL':atlas.colorspace_settings.name='Non-Color';bpy.ops.object.bake(type=kind,use_clear=False,margin=8,normal_space='TANGENT')
        else:bpy.ops.object.bake(type=kind,pass_filter={'COLOR'},use_clear=False,margin=8)
        atlas.filepath_raw=str(GLB.parent/f'kudzu-forest-{name}.png');atlas.file_format='PNG';atlas.save();atlas.pack();images.append(atlas)
    baked=plain_material('Kudzu Forest - Runtime PBR',(.07,.004,.1),.58);n=baked.node_tree.nodes;l=baked.node_tree.links;p=n.get('Principled BSDF');p.inputs['Specular IOR Level'].default_value=.25
    color=n.new('ShaderNodeTexImage');color.image=images[0];l.new(color.outputs['Color'],p.inputs['Base Color']);tex=n.new('ShaderNodeTexImage');tex.image=images[1];nm=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
    for o in objects:o.data.materials[0]=baked
    s.cycles.samples=32
    print('Shared 2048 base-color and 1024 tangent-normal textures baked; procedural source retained.')


def export_runtime():
    reset();rig=obj('Kudzu AvatarRig');bpy.ops.object.select_all(action='DESELECT')
    for o in bpy.context.scene.objects:
        if o.type in {'MESH','ARMATURE'}:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,use_active_scene=True,export_animations=False,export_skins=True,export_morph=True,export_morph_normal=True,export_extras=True,export_yup=True,export_cameras=False,export_lights=False)
    rig.hide_set(True);bpy.context.scene['status']='Isolated review rig; physical ZED/Orin and visual acceptance still required.';bpy.ops.wm.save_as_mainfile(filepath=str(OUT))


def validate():
    from reference_rig_checks import validate as check
    return check('Kudzu','Kudzu AvatarRig',QA,obj('Kudzu Head')['mouthPatchStart'],reset,rotate,expression)

def view(angle=False):
    s=bpy.context.scene;s.camera.location=(4,-8,3) if angle else (0,-8,1.68);s.camera.rotation_euler=(Vector((0,0,1.68))-s.camera.location).to_track_quat('-Z','Y').to_euler()
    for o in s.objects:
        if o.type in {'CAMERA','LIGHT','ARMATURE'}:o.hide_set(True)
    for a in bpy.context.screen.areas:
        if a.type=='VIEW_3D':
            sp=a.spaces.active;sp.shading.type='MATERIAL';sp.overlay.show_cursor=False;sp.overlay.show_floor=False;sp.overlay.show_axis_x=False;sp.overlay.show_axis_y=False
            sp.region_3d.view_rotation=Quaternion((1,0,0),math.pi/2);sp.region_3d.view_location=(-1.35,0,1.7);sp.region_3d.view_distance=5.3;sp.region_3d.view_perspective='ORTHO'


def render(name):bpy.context.scene.render.filepath=str(QA/(name+'.png'));bpy.ops.render.render(write_still=True)
