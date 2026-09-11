"""Four-digit, jointed replacement hands for fused source meshes."""
import math
import bpy
import bmesh
from mathutils import Vector
from build_avatar_fleet import Mesh, material

COLORS={'orbit':'#b89ac8','pearl':'#d9b7c0','juno':'#ed9b53','fuzz':'#cba7c1',
        'clementine':'#8abe5e','coral':'#c47f90','sprout':'#806186','atl':'#9abb8b'}


def smooth(a,b,value):
    t=max(0,min(1,(value-a)/(b-a)))
    return t*t*(3-2*t)


def fit_wrist_centers(body,rig):
    fits={}
    for side in ['L','R']:
        bone=rig.data.bones['Hand.'+side];origin=bone.head_local;d=(bone.tail_local-origin).normalized()
        length=max(.20,min(.32,bone.length*1.25));points=[]
        groups={body.vertex_groups[n+'.'+side].index for n in ['UpperArm','Forearm','Hand']}
        for edge in body.data.edges:
            a,b=[body.data.vertices[i] for i in edge.vertices]
            weight=sum(g.weight for vertex in [a,b] for g in vertex.groups if g.group in groups)/2
            if weight<.55:continue
            da=(a.co-origin).dot(d)+length*.2;db=(b.co-origin).dot(d)+length*.2
            if da*db>=0:continue
            point=a.co.lerp(b.co,da/(da-db))
            if (point-origin).length<length*3:points.append(point)
        assert len(points)>12,(body.name,side,'missing wrist cross-section')
        delta=sum(points,Vector())/len(points)-origin;delta-=d*delta.dot(d)
        assert delta.length<.30,(body.name,side,'wrist requires a new landmark fit',delta[:])
        fits[side]=delta
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for side,delta in fits.items():
        hand=rig.data.edit_bones['Hand.'+side];hand.head+=delta;hand.tail+=delta
        rig.data.edit_bones['Forearm.'+side].tail=hand.head
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    rig['wristFitOffsets']={side:list(delta) for side,delta in fits.items()}


def build_hands(body,rig,name):
    objects=[]
    for side in ['L','R']:
        hand=rig.data.bones['Hand.'+side]
        origin=hand.head_local.copy();d=(hand.tail_local-origin).normalized()
        n=Vector((0,-1,0));n=(n-d*n.dot(d)).normalized();w=d.cross(n).normalized()
        if side=='R':w=-w
        length=max(.20,min(.32,hand.length*1.25))
        def point(x,y,z=0):return origin+(w*x+d*y+n*z)*length
        # Preserve the forearm and sleeve; the new wrist overlaps this cut.
        bm=bmesh.new();bm.from_mesh(body.data)
        deform=bm.verts.layers.deform.active
        arm_groups={body.vertex_groups[b+'.'+side].index for b in ['UpperArm','Forearm','Hand']}
        def arm_weight(face):return sum(sum(v[deform].get(g,0) for g in arm_groups) for v in face.verts)/len(face.verts)
        crop_radius=2.5
        local_radius=3
        local_faces=[face for face in bm.faces if arm_weight(face)>.55 and (face.calc_center_median()-origin).length<length*local_radius]
        local_edges={edge for face in local_faces for edge in face.edges}
        local_verts={v for face in local_faces for v in face.verts}
        bmesh.ops.bisect_plane(bm,geom=[*local_faces,*local_edges,*local_verts],dist=.00001,
                              plane_co=origin-d*length*.20,plane_no=d,clear_inner=False,clear_outer=False)
        faces=[]
        for face in bm.faces:
            offset=face.calc_center_median()-origin;along=offset.dot(d)
            if arm_weight(face)>.55 and along>-.20*length+.00001 and along<length*3 and (offset-d*along).length<length*crop_radius:
                faces.append(face)
        removed=set(faces)
        seam={edge for face in faces for edge in face.edges if any(f not in removed for f in edge.link_faces)}
        radii=[];cut_points=[]
        for vertex in {v for edge in seam for v in edge.verts}:
            offset=vertex.co-origin;along=offset.dot(d)
            if abs(along+length*.20)<.0001:
                radii.append((offset-d*along).length);cut_points.append(vertex.co.copy())
        cuff_radius=sorted(radii)[len(radii)//2] if radii else length*.34
        length=max(length,min(.40,cuff_radius*2.8))
        wrist_radius=max(length*.20,min(length*.34,cuff_radius*.85))
        bmesh.ops.delete(bm,geom=faces,context='FACES_ONLY')
        cap=material(name+' wrist closure '+side,COLORS[name],.55)
        body.data.materials.append(cap);cap_index=len(body.data.materials)-1
        closures=bmesh.ops.holes_fill(bm,edges=[e for e in seam if e.is_valid and e.is_boundary],sides=0)['faces']
        for face in closures:face.material_index=cap_index;face.smooth=True
        if closures:bmesh.ops.triangulate(bm,faces=closures)
        bmesh.ops.triangulate(bm,faces=[face for face in bm.faces if len(face.verts)>3])
        bm.to_mesh(body.data);bm.free();body.data.update()
        chains={}
        for digit,x,size in [('Index',-.24,.59),('Middle',0,.65),('Ring',.24,.54)]:
            a=point(x,.47);direction=(d+w*x*.22).normalized()
            chains[digit]=[a+direction*length*size*t for t in [0,.44,.77,1]]
        chains['Thumb']=[point(-.25,.17),point(-.49,.29),point(-.60,.43),point(-.66,.55)]
        bpy.context.view_layer.objects.active=rig;rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        for digit,points in chains.items():
            for i in range(3):
                bone=rig.data.edit_bones.new(f'{digit}{i+1}.{side}')
                bone.head=points[i];bone.tail=points[i+1];bone.align_roll(n)
                bone.parent=rig.data.edit_bones['Hand.'+side if i==0 else f'{digit}{i}.{side}']
                bone.use_connect=i>0
        bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
        for digit in chains:
            for i in range(3):
                bone=rig.data.bones[f'{digit}{i+1}.{side}']
                bone['fingerDigit']=digit;bone['fingerJoint']=i;bone['curlAxis']=[1,0,0]
        mesh=Mesh();skin=material(name+' hand skin',COLORS[name],.55)
        # Remesh the overlapping palm and finger volumes into a continuous surface.
        def ellipsoid(center,scales):
            start=len(mesh.v);mesh.ellipsoid((0,0,0),scales,skin,n=20,rings=14)
            for i in range(start,len(mesh.v)):
                x,y,z=mesh.v[i];mesh.v[i]=tuple(center+w*x+d*y+n*z)
        ellipsoid(point(0,.24),(.35*length,.35*length,.17*length))
        mesh.tube([point(0,-.40),point(0,-.15),point(0,.20)],[wrist_radius,wrist_radius*.9,.30*length],skin,n=20)
        for digit,points in chains.items():
            radius=length*(.105 if digit=='Thumb' else .095)
            mesh.tube(points,[radius,radius*.94,radius*.82,radius*.55],skin,n=14)
            for p,r in zip(points,[radius,radius*.94,radius*.82,radius*.55]):
                mesh.ellipsoid(p,(r,r,r),skin,n=16,rings=10)
        obj=mesh.object(name.title()+'ArticulatedHand'+side)
        bpy.context.view_layer.objects.active=obj;obj.select_set(True)
        obj.data.remesh_voxel_size=length*.024;bpy.ops.object.voxel_remesh()
        modifier=obj.modifiers.new('Smooth finger webbing','SMOOTH');modifier.factor=.65;modifier.iterations=3
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        for poly in obj.data.polygons:poly.use_smooth=True
        groups={b.name:obj.vertex_groups.new(name=b.name) for b in rig.data.bones}
        for vertex in obj.data.vertices:
            p=vertex.co
            distances={}
            for digit,points in chains.items():
                distance=1e9
                for a,b in zip(points,points[1:]):
                    axis=b-a;t=max(0,min(1,(p-a).dot(axis)/axis.length_squared))
                    distance=min(distance,(p-a-axis*t).length)
                distances[digit]=distance
            digit=min(distances,key=distances.get);points=chains[digit]
            axis=(points[-1]-points[0]).normalized();total=(points[-1]-points[0]).length
            t=(p-points[0]).dot(axis)/total
            active=smooth(-.16,.12,t)
            first=1-smooth(.32,.55,t);third=smooth(.66,.89,t)
            weights={'Hand.'+side:1-active,f'{digit}1.{side}':active*first,
                     f'{digit}2.{side}':active*(1-first-third),f'{digit}3.{side}':active*third}
            wrist=(p-origin).dot(d)
            forearm=(1-smooth(-.11,.025,wrist))*weights['Hand.'+side]
            weights['Hand.'+side]-=forearm;weights['Forearm.'+side]=forearm
            for key,value in weights.items():
                if value>1e-7:groups[key].add([vertex.index],value,'REPLACE')
        if name=='pearl':
            tips=material('Pearl orange fingertips','#e99661',.5);obj.data.materials.append(tips)
            for poly in obj.data.polygons:
                center=poly.center
                if min((center-points[-1]).length for points in chains.values())<length*.19:poly.material_index=1
        mod=obj.modifiers.new('Articulated hand skin','ARMATURE');mod.object=rig;obj.parent=rig
        obj['assetRole']='articulated-hand';obj['handSide']=side;obj['fingerDigits']=['Thumb','Index','Middle','Ring']
        obj.select_set(False);objects.append(obj)
    rig['bodyRig']='FK limbs with three-joint thumb and three independently articulated fingers per hand'
    return objects
